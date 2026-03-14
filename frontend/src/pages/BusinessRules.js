import { useEffect, useState } from 'react';
import axios from 'axios';
import { Plus, Trash2, CheckCircle, Ban, Star, AlertCircle } from 'lucide-react';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const RULE_TYPES = [
  { value: 'ALLOW', label: 'ALLOW - Autoriser', icon: CheckCircle, color: 'text-green-600', bg: 'bg-green-100' },
  { value: 'FORBID', label: 'FORBID - Interdire', icon: Ban, color: 'text-red-600', bg: 'bg-red-100' },
  { value: 'PREFER', label: 'PREFER - Préférer', icon: Star, color: 'text-amber-600', bg: 'bg-amber-100' }
];

export default function BusinessRules() {
  const [rules, setRules] = useState([]);
  const [machines, setMachines] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    tache_id: '',
    centre_de_charge_id: '',
    article_id: '',
    rule_type: 'ALLOW',
    machine_id: '',
    active: true
  });
  const [formError, setFormError] = useState('');

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [rulesRes, machinesRes] = await Promise.all([
        axios.get(`${API}/rules`),
        axios.get(`${API}/machines`)
      ]);
      setRules(rulesRes.data);
      setMachines(machinesRes.data);
    } catch (error) {
      console.error('Error:', error);
      toast.error('Erreur lors du chargement');
    }
  };

  const validateForm = () => {
    if (!formData.tache_id && !formData.centre_de_charge_id) {
      setFormError('Au moins tache_id OU centre_de_charge_id doit être renseigné');
      return false;
    }
    if (!formData.machine_id) {
      setFormError('La machine cible est obligatoire');
      return false;
    }
    if (!formData.name.trim()) {
      setFormError('Le nom de la règle est obligatoire');
      return false;
    }
    setFormError('');
    return true;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validateForm()) return;

    try {
      const cleanData = {
        name: formData.name.trim(),
        rule_type: formData.rule_type,
        machine_id: formData.machine_id,
        active: formData.active
      };
      if (formData.tache_id.trim()) cleanData.tache_id = formData.tache_id.trim();
      if (formData.centre_de_charge_id.trim()) cleanData.centre_de_charge_id = formData.centre_de_charge_id.trim();
      if (formData.article_id.trim()) cleanData.article_id = formData.article_id.trim();

      const response = await axios.post(`${API}/rules`, cleanData);
      setRules([...rules, response.data]);
      toast.success(`Règle "${response.data.name}" créée: ${response.data.rule_type} sur ${response.data.machine_id}`);
      
      setFormData({
        name: '',
        tache_id: '',
        centre_de_charge_id: '',
        article_id: '',
        rule_type: 'ALLOW',
        machine_id: '',
        active: true
      });
      setShowForm(false);
      setFormError('');
    } catch (error) {
      toast.error(`Erreur: ${error.response?.data?.detail || error.message}`);
    }
  };

  const handleDelete = async (id, name) => {
    if (!window.confirm(`Supprimer la règle "${name}" ?`)) return;
    try {
      await axios.delete(`${API}/rules/${id}`);
      setRules(rules.filter(r => r.id !== id));
      toast.success(`Règle "${name}" supprimée`);
    } catch (error) {
      toast.error('Erreur lors de la suppression');
    }
  };

  const getRuleTypeInfo = (type) => {
    return RULE_TYPES.find(t => t.value === type?.toUpperCase()) || RULE_TYPES[0];
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-2xl font-semibold text-slate-800">Règles Métier</h3>
          <p className="text-sm text-slate-500 mt-1">
            Règles d'affectation machine basées sur tâche et centre de charge
          </p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="inline-flex items-center gap-2 bg-slate-900 text-white hover:bg-slate-800 rounded-sm px-4 py-2 text-sm font-medium"
        >
          <Plus size={16} />
          Nouvelle Règle
        </button>
      </div>

      {showForm && (
        <div className="bg-white border border-slate-200 rounded-sm shadow-sm p-5">
          <h4 className="text-lg font-semibold text-slate-800 mb-4">Nouvelle Règle d'Affectation</h4>
          
          {formError && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-sm flex items-center gap-2 text-red-700 text-sm">
              <AlertCircle size={16} />
              {formError}
            </div>
          )}
          
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="text-xs font-semibold uppercase tracking-wider text-slate-500 block mb-2">
                Nom de la règle *
              </label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="Ex: Interdire PLIAGE sur PLIEUSE_01"
                className="w-full h-9 rounded-sm border border-slate-300 px-3 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-slate-900"
                required
              />
            </div>

            <div className="bg-blue-50 border border-blue-200 rounded-sm p-4">
              <p className="text-sm font-semibold text-blue-900 mb-1">Critères de Ciblage (codes métier)</p>
              <p className="text-xs text-blue-700 mb-3">
                Au moins tache_id ou centre_de_charge_id doit être défini.
              </p>
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="text-xs font-semibold text-blue-700 block mb-1">Tâche ID</label>
                  <input
                    type="text"
                    value={formData.tache_id}
                    onChange={(e) => setFormData({ ...formData, tache_id: e.target.value.toUpperCase() })}
                    placeholder="Ex: PLIAGE"
                    className="w-full h-9 rounded-sm border border-blue-300 bg-white px-3 py-1 text-sm"
                  />
                </div>
                <div>
                  <label className="text-xs font-semibold text-blue-700 block mb-1">Centre de Charge ID</label>
                  <input
                    type="text"
                    value={formData.centre_de_charge_id}
                    onChange={(e) => setFormData({ ...formData, centre_de_charge_id: e.target.value.toUpperCase() })}
                    placeholder="Ex: PLI01"
                    className="w-full h-9 rounded-sm border border-blue-300 bg-white px-3 py-1 text-sm"
                  />
                </div>
                <div>
                  <label className="text-xs font-semibold text-blue-700 block mb-1">Article ID (optionnel)</label>
                  <input
                    type="text"
                    value={formData.article_id}
                    onChange={(e) => setFormData({ ...formData, article_id: e.target.value })}
                    placeholder="Ex: ART001"
                    className="w-full h-9 rounded-sm border border-blue-300 bg-white px-3 py-1 text-sm"
                  />
                </div>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="bg-amber-50 border border-amber-200 rounded-sm p-4">
                <label className="text-xs font-semibold text-amber-700 block mb-2">Type de Règle *</label>
                <select
                  value={formData.rule_type}
                  onChange={(e) => setFormData({ ...formData, rule_type: e.target.value })}
                  className="w-full h-10 rounded-sm border border-amber-300 bg-white px-3 py-1 text-sm"
                  required
                >
                  {RULE_TYPES.map((type) => (
                    <option key={type.value} value={type.value}>{type.label}</option>
                  ))}
                </select>
              </div>
              
              <div className="bg-green-50 border border-green-200 rounded-sm p-4">
                <label className="text-xs font-semibold text-green-700 block mb-2">Machine Cible (code) *</label>
                <select
                  value={formData.machine_id}
                  onChange={(e) => setFormData({ ...formData, machine_id: e.target.value })}
                  className="w-full h-10 rounded-sm border border-green-300 bg-white px-3 py-1 text-sm"
                  required
                >
                  <option value="">-- Sélectionner --</option>
                  {machines.map((machine) => (
                    <option key={machine.id} value={machine.id}>
                      {machine.id} ({machine.centre_de_charge_id || machine.work_center_id})
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="active"
                checked={formData.active}
                onChange={(e) => setFormData({ ...formData, active: e.target.checked })}
                className="rounded border-slate-300"
              />
              <label htmlFor="active" className="text-sm text-slate-700">Règle active</label>
            </div>

            <div className="flex gap-2">
              <button type="submit" className="bg-slate-900 text-white hover:bg-slate-800 rounded-sm px-4 py-2 text-sm font-medium">
                Créer la règle
              </button>
              <button type="button" onClick={() => { setShowForm(false); setFormError(''); }} className="bg-white text-slate-700 border border-slate-300 hover:bg-slate-50 rounded-sm px-4 py-2 text-sm font-medium">
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
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase">Nom</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase">Tâche ID</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase">Centre</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase">Article</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase">Type</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase">Machine</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase">Actif</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody>
            {rules.map((rule) => {
              const typeInfo = getRuleTypeInfo(rule.rule_type);
              const TypeIcon = typeInfo.icon;
              return (
                <tr key={rule.id} className="border-b border-slate-100 hover:bg-slate-50">
                  <td className="px-4 py-3 text-sm text-slate-900 font-medium">{rule.name}</td>
                  <td className="px-4 py-3 text-xs font-mono">
                    {rule.tache_id ? (
                      <span className="bg-blue-100 text-blue-800 px-2 py-0.5 rounded">{rule.tache_id}</span>
                    ) : <span className="text-slate-400">-</span>}
                  </td>
                  <td className="px-4 py-3 text-xs font-mono">
                    {rule.centre_de_charge_id ? (
                      <span className="bg-purple-100 text-purple-800 px-2 py-0.5 rounded">{rule.centre_de_charge_id}</span>
                    ) : <span className="text-slate-400">-</span>}
                  </td>
                  <td className="px-4 py-3 text-xs font-mono">
                    {rule.article_id ? (
                      <span className="bg-orange-100 text-orange-800 px-2 py-0.5 rounded">{rule.article_id}</span>
                    ) : <span className="text-slate-400">-</span>}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex items-center gap-1 px-2 py-1 rounded text-xs font-semibold ${typeInfo.bg} ${typeInfo.color}`}>
                      <TypeIcon size={12} />
                      {rule.rule_type?.toUpperCase()}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="bg-slate-100 text-slate-800 px-2 py-0.5 rounded text-xs font-mono font-medium">
                      {rule.machine_id}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded text-xs font-semibold ${rule.active ? 'bg-green-100 text-green-700' : 'bg-slate-100 text-slate-500'}`}>
                      {rule.active ? 'Oui' : 'Non'}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <button onClick={() => handleDelete(rule.id, rule.name)} className="text-red-600 hover:text-red-800 p-1" title="Supprimer">
                      <Trash2 size={16} />
                    </button>
                  </td>
                </tr>
              );
            })}
            {rules.length === 0 && (
              <tr>
                <td colSpan={8} className="px-4 py-8 text-center text-sm text-slate-500">
                  Aucune règle. Cliquez sur "Nouvelle Règle" pour en créer une.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="bg-slate-50 border border-slate-200 rounded-sm p-5">
        <h4 className="text-lg font-semibold text-slate-800 mb-3">Types de Règles</h4>
        <div className="grid grid-cols-3 gap-4 text-sm">
          <div className="flex items-start gap-2">
            <CheckCircle className="text-green-600 mt-0.5" size={16} />
            <div>
              <p className="font-semibold text-slate-800">ALLOW</p>
              <p className="text-slate-600">Autorise explicitement une machine.</p>
            </div>
          </div>
          <div className="flex items-start gap-2">
            <Ban className="text-red-600 mt-0.5" size={16} />
            <div>
              <p className="font-semibold text-slate-800">FORBID</p>
              <p className="text-slate-600">Interdit une machine (exclue du planning).</p>
            </div>
          </div>
          <div className="flex items-start gap-2">
            <Star className="text-amber-600 mt-0.5" size={16} />
            <div>
              <p className="font-semibold text-slate-800">PREFER</p>
              <p className="text-slate-600">Préfère une machine (prioritaire).</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
