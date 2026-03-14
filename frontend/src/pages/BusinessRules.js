import { useEffect, useState } from 'react';
import axios from 'axios';
import { Plus, Trash2, AlertCircle, CheckCircle, Ban, Star } from 'lucide-react';
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
    task_id: '',
    work_center_id: '',
    article_id: '',
    rule_type: 'ALLOW',
    machine_id: '',
    active: true
  });
  const [formError, setFormError] = useState('');

  useEffect(() => {
    fetchRules();
    fetchMachines();
  }, []);

  const fetchRules = async () => {
    try {
      const response = await axios.get(`${API}/rules`);
      setRules(response.data);
    } catch (error) {
      console.error('Error fetching rules:', error);
      toast.error('Erreur lors du chargement des règles');
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

  const validateForm = () => {
    // Validation: au moins task_id ou work_center_id
    if (!formData.task_id && !formData.work_center_id) {
      setFormError('Au moins task_id OU work_center_id doit être renseigné');
      return false;
    }
    // Validation: article_id seul non autorisé
    if (formData.article_id && !formData.task_id && !formData.work_center_id) {
      setFormError('article_id ne peut pas être utilisé seul');
      return false;
    }
    // Validation: machine_id obligatoire
    if (!formData.machine_id) {
      setFormError('La machine cible est obligatoire');
      return false;
    }
    // Validation: nom obligatoire
    if (!formData.name.trim()) {
      setFormError('Le nom de la règle est obligatoire');
      return false;
    }
    setFormError('');
    return true;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }

    try {
      const cleanData = {
        name: formData.name.trim(),
        rule_type: formData.rule_type,
        machine_id: formData.machine_id,
        active: formData.active
      };
      
      // N'envoyer que les champs non vides
      if (formData.task_id.trim()) cleanData.task_id = formData.task_id.trim();
      if (formData.work_center_id.trim()) cleanData.work_center_id = formData.work_center_id.trim();
      if (formData.article_id.trim()) cleanData.article_id = formData.article_id.trim();

      const response = await axios.post(`${API}/rules`, cleanData);
      const savedRule = response.data;
      
      // Mise à jour immédiate de l'état local
      setRules(prevRules => [...prevRules, savedRule]);
      
      // Message de confirmation
      const machineName = machines.find(m => m.id === savedRule.machine_id)?.name || savedRule.machine_id;
      toast.success(
        `Règle "${savedRule.name}" créée: ${savedRule.rule_type} sur ${machineName}`,
        { duration: 4000 }
      );
      
      // Reset formulaire
      setFormData({
        name: '',
        task_id: '',
        work_center_id: '',
        article_id: '',
        rule_type: 'ALLOW',
        machine_id: '',
        active: true
      });
      setShowForm(false);
      setFormError('');
      
    } catch (error) {
      console.error('Error creating rule:', error);
      toast.error(`Erreur: ${error.response?.data?.detail || error.message}`);
    }
  };

  const handleDelete = async (id, name) => {
    if (!window.confirm(`Supprimer la règle "${name}" ?`)) return;
    try {
      await axios.delete(`${API}/rules/${id}`);
      setRules(prevRules => prevRules.filter(r => r.id !== id));
      toast.success(`Règle "${name}" supprimée`);
    } catch (error) {
      toast.error('Erreur lors de la suppression');
    }
  };

  const getRuleTypeInfo = (type) => {
    return RULE_TYPES.find(t => t.value === type?.toUpperCase()) || RULE_TYPES[0];
  };

  const getMachineName = (machineId) => {
    const machine = machines.find(m => m.id === machineId);
    return machine?.name || machineId;
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-2xl font-semibold text-slate-800">Règles Métier</h3>
          <p className="text-sm text-slate-500 mt-1">
            Règles d'affectation machine : ALLOW, FORBID, PREFER
          </p>
        </div>
        <button
          data-testid="create-rule-btn"
          onClick={() => setShowForm(!showForm)}
          className="inline-flex items-center gap-2 bg-slate-900 text-white hover:bg-slate-800 rounded-sm px-4 py-2 text-sm font-medium transition-colors shadow-sm"
        >
          <Plus size={16} />
          Nouvelle Règle
        </button>
      </div>

      {/* Formulaire de création */}
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
            {/* Nom de la règle */}
            <div>
              <label className="text-xs font-semibold uppercase tracking-wider text-slate-500 block mb-2">
                Nom de la règle *
              </label>
              <input
                data-testid="rule-name-input"
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="Ex: Interdire USINAGE sur M001"
                className="w-full h-9 rounded-sm border border-slate-300 bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus:outline-none focus:ring-1 focus:ring-slate-900"
                required
              />
            </div>

            {/* Critères de ciblage */}
            <div className="bg-blue-50 border border-blue-200 rounded-sm p-4">
              <p className="text-sm font-semibold text-blue-900 mb-1">Critères de Ciblage</p>
              <p className="text-xs text-blue-700 mb-3">
                Au moins task_id ou work_center_id doit être défini. article_id est optionnel mais ne peut pas être seul.
              </p>
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="text-xs font-semibold text-blue-700 block mb-1">
                    Task ID
                  </label>
                  <input
                    data-testid="task-id-input"
                    type="text"
                    value={formData.task_id}
                    onChange={(e) => setFormData({ ...formData, task_id: e.target.value })}
                    placeholder="Ex: USINAGE"
                    className="w-full h-9 rounded-sm border border-blue-300 bg-white px-3 py-1 text-sm shadow-sm transition-colors focus:outline-none focus:ring-1 focus:ring-blue-600"
                  />
                </div>
                <div>
                  <label className="text-xs font-semibold text-blue-700 block mb-1">
                    Work Center ID
                  </label>
                  <input
                    data-testid="work-center-id-input"
                    type="text"
                    value={formData.work_center_id}
                    onChange={(e) => setFormData({ ...formData, work_center_id: e.target.value })}
                    placeholder="Ex: WC001"
                    className="w-full h-9 rounded-sm border border-blue-300 bg-white px-3 py-1 text-sm shadow-sm transition-colors focus:outline-none focus:ring-1 focus:ring-blue-600"
                  />
                </div>
                <div>
                  <label className="text-xs font-semibold text-blue-700 block mb-1">
                    Article ID (optionnel)
                  </label>
                  <input
                    data-testid="article-id-input"
                    type="text"
                    value={formData.article_id}
                    onChange={(e) => setFormData({ ...formData, article_id: e.target.value })}
                    placeholder="Ex: ART001"
                    className="w-full h-9 rounded-sm border border-blue-300 bg-white px-3 py-1 text-sm shadow-sm transition-colors focus:outline-none focus:ring-1 focus:ring-blue-600"
                  />
                </div>
              </div>
            </div>

            {/* Type de règle et Machine */}
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-amber-50 border border-amber-200 rounded-sm p-4">
                <label className="text-xs font-semibold text-amber-700 block mb-2">
                  Type de Règle *
                </label>
                <select
                  data-testid="rule-type-select"
                  value={formData.rule_type}
                  onChange={(e) => setFormData({ ...formData, rule_type: e.target.value })}
                  className="w-full h-10 rounded-sm border border-amber-300 bg-white px-3 py-1 text-sm shadow-sm transition-colors focus:outline-none focus:ring-1 focus:ring-amber-600"
                  required
                >
                  {RULE_TYPES.map((type) => (
                    <option key={type.value} value={type.value}>
                      {type.label}
                    </option>
                  ))}
                </select>
                <p className="text-xs text-amber-600 mt-2">
                  {formData.rule_type === 'ALLOW' && 'La machine sera explicitement autorisée'}
                  {formData.rule_type === 'FORBID' && 'La machine sera exclue'}
                  {formData.rule_type === 'PREFER' && 'La machine sera prioritaire si possible'}
                </p>
              </div>
              
              <div className="bg-green-50 border border-green-200 rounded-sm p-4">
                <label className="text-xs font-semibold text-green-700 block mb-2">
                  Machine Cible *
                </label>
                <select
                  data-testid="machine-id-select"
                  value={formData.machine_id}
                  onChange={(e) => setFormData({ ...formData, machine_id: e.target.value })}
                  className="w-full h-10 rounded-sm border border-green-300 bg-white px-3 py-1 text-sm shadow-sm transition-colors focus:outline-none focus:ring-1 focus:ring-green-600"
                  required
                >
                  <option value="">-- Sélectionner une machine --</option>
                  {machines.map((machine) => (
                    <option key={machine.id} value={machine.id}>
                      {machine.name} ({machine.work_center_id || 'N/A'})
                    </option>
                  ))}
                </select>
                {machines.length === 0 && (
                  <p className="text-xs text-red-600 mt-2">
                    Aucune machine disponible. Créez des machines d'abord.
                  </p>
                )}
              </div>
            </div>

            {/* Active toggle */}
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="active-checkbox"
                checked={formData.active}
                onChange={(e) => setFormData({ ...formData, active: e.target.checked })}
                className="rounded border-slate-300"
              />
              <label htmlFor="active-checkbox" className="text-sm text-slate-700">
                Règle active
              </label>
            </div>

            {/* Boutons */}
            <div className="flex gap-2 pt-2">
              <button
                type="submit"
                data-testid="submit-rule-btn"
                className="bg-slate-900 text-white hover:bg-slate-800 rounded-sm px-4 py-2 text-sm font-medium transition-colors shadow-sm"
              >
                Créer la règle
              </button>
              <button
                type="button"
                onClick={() => {
                  setShowForm(false);
                  setFormError('');
                }}
                className="bg-white text-slate-700 border border-slate-300 hover:bg-slate-50 rounded-sm px-4 py-2 text-sm font-medium transition-colors"
              >
                Annuler
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Tableau des règles */}
      <div className="bg-white border border-slate-200 rounded-sm shadow-sm overflow-hidden">
        <table className="w-full">
          <thead className="bg-slate-50 border-b border-slate-200">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Nom</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Task ID</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Work Center</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Article ID</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Type</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Machine</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Actif</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody>
            {rules.map((rule) => {
              const typeInfo = getRuleTypeInfo(rule.rule_type);
              const TypeIcon = typeInfo.icon;
              return (
                <tr key={rule.id} className="border-b border-slate-100 hover:bg-slate-50 transition-colors" data-testid="rule-row">
                  <td className="px-4 py-3 text-sm text-slate-900 font-medium">{rule.name}</td>
                  <td className="px-4 py-3 text-xs font-mono">
                    {rule.task_id ? (
                      <span className="bg-blue-100 text-blue-800 px-2 py-0.5 rounded">{rule.task_id}</span>
                    ) : (
                      <span className="text-slate-400">-</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-xs font-mono">
                    {rule.work_center_id ? (
                      <span className="bg-purple-100 text-purple-800 px-2 py-0.5 rounded">{rule.work_center_id}</span>
                    ) : (
                      <span className="text-slate-400">-</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-xs font-mono">
                    {rule.article_id ? (
                      <span className="bg-orange-100 text-orange-800 px-2 py-0.5 rounded">{rule.article_id}</span>
                    ) : (
                      <span className="text-slate-400">-</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex items-center gap-1 px-2 py-1 rounded text-xs font-semibold ${typeInfo.bg} ${typeInfo.color}`}>
                      <TypeIcon size={12} />
                      {rule.rule_type?.toUpperCase()}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-slate-700">
                    <span className="bg-slate-100 text-slate-800 px-2 py-0.5 rounded text-xs font-medium">
                      {getMachineName(rule.machine_id)}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`px-2 py-0.5 rounded text-xs font-semibold ${
                        rule.active ? 'bg-green-100 text-green-700' : 'bg-slate-100 text-slate-500'
                      }`}
                    >
                      {rule.active ? 'Oui' : 'Non'}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <button
                      data-testid="delete-rule-btn"
                      onClick={() => handleDelete(rule.id, rule.name)}
                      className="text-red-600 hover:text-red-800 transition-colors p-1"
                      title="Supprimer"
                    >
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

      {/* Aide */}
      <div className="bg-slate-50 border border-slate-200 rounded-sm p-5">
        <h4 className="text-lg font-semibold text-slate-800 mb-3">Types de Règles</h4>
        <div className="grid grid-cols-3 gap-4 text-sm">
          <div className="flex items-start gap-2">
            <CheckCircle className="text-green-600 mt-0.5" size={16} />
            <div>
              <p className="font-semibold text-slate-800">ALLOW</p>
              <p className="text-slate-600">Autorise explicitement une machine pour les critères définis.</p>
            </div>
          </div>
          <div className="flex items-start gap-2">
            <Ban className="text-red-600 mt-0.5" size={16} />
            <div>
              <p className="font-semibold text-slate-800">FORBID</p>
              <p className="text-slate-600">Interdit une machine. Elle sera exclue du planning.</p>
            </div>
          </div>
          <div className="flex items-start gap-2">
            <Star className="text-amber-600 mt-0.5" size={16} />
            <div>
              <p className="font-semibold text-slate-800">PREFER</p>
              <p className="text-slate-600">Préfère une machine si possible (priorité dans le moteur).</p>
            </div>
          </div>
        </div>
        
        <h4 className="text-lg font-semibold text-slate-800 mt-5 mb-3">Exemples</h4>
        <div className="space-y-2 text-sm text-slate-700">
          <p><strong>task_id=USINAGE, machine=M001, FORBID</strong> : Interdit l'usinage sur M001</p>
          <p><strong>work_center_id=WC002, machine=M003, PREFER</strong> : Préfère M003 pour le centre WC002</p>
          <p><strong>task_id=ASSEMBLAGE + work_center_id=WC001, machine=M002, ALLOW</strong> : Autorise M002 pour assemblage sur WC001</p>
        </div>
      </div>
    </div>
  );
}
