import { useEffect, useState } from 'react';
import axios from 'axios';
import { Plus, Trash2, Edit2 } from 'lucide-react';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const ruleTypes = [
  { value: 'compatibility', label: 'Compatibilité' },
  { value: 'preference', label: 'Préférence' },
  { value: 'setup_time', label: 'Temps de Réglage' },
  { value: 'prohibition', label: 'Interdiction' }
];

const actionTypes = [
  { value: 'allow', label: 'Autoriser' },
  { value: 'forbid', label: 'Interdire' },
  { value: 'penalty', label: 'Pénalité' },
  { value: 'setup_time', label: 'Temps de Réglage' },
  { value: 'preferred_machine', label: 'Machine Préférée' }
];

export default function BusinessRules() {
  const [rules, setRules] = useState([]);
  const [machines, setMachines] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    rule_type: 'compatibility',
    is_hard: true,
    task_id: '',
    work_center_id: '',
    machine_id: '',
    article_id: '',
    condition_operator: 'equals',
    condition_value: '',
    action_type: 'allow',
    action_value: '',
    active: true,
    description: ''
  });

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

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      // Ne pas envoyer les champs vides
      const cleanData = { ...formData };
      if (!cleanData.task_id) delete cleanData.task_id;
      if (!cleanData.work_center_id) delete cleanData.work_center_id;
      if (!cleanData.machine_id) delete cleanData.machine_id;
      if (!cleanData.article_id) delete cleanData.article_id;
      if (!cleanData.condition_value) delete cleanData.condition_value;
      if (!cleanData.action_value) delete cleanData.action_value;
      if (!cleanData.description) delete cleanData.description;

      await axios.post(`${API}/rules`, cleanData);
      toast.success('Règle créée');
      setFormData({
        name: '',
        rule_type: 'compatibility',
        is_hard: true,
        task_id: '',
        work_center_id: '',
        machine_id: '',
        article_id: '',
        condition_operator: 'equals',
        condition_value: '',
        action_type: 'allow',
        action_value: '',
        active: true,
        description: ''
      });
      setShowForm(false);
      fetchRules();
    } catch (error) {
      toast.error('Erreur lors de la création');
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Confirmer la suppression ?')) return;
    try {
      await axios.delete(`${API}/rules/${id}`);
      toast.success('Règle supprimée');
      fetchRules();
    } catch (error) {
      toast.error('Erreur lors de la suppression');
    }
  };

  const getRuleSummary = (rule) => {
    const parts = [];
    if (rule.task_id) parts.push(`Task: ${rule.task_id}`);
    if (rule.work_center_id) parts.push(`WC: ${rule.work_center_id}`);
    if (rule.machine_id) parts.push(`Machine: ${rule.machine_id}`);
    if (rule.article_id) parts.push(`Article: ${rule.article_id}`);
    return parts.join(' + ') || 'Générale';
  };

  const getActionSummary = (rule) => {
    if (rule.action_type === 'penalty' && rule.action_value) {
      return `Pénalité: ${rule.action_value}`;
    }
    if (rule.action_type === 'setup_time' && rule.action_value) {
      return `+${rule.action_value} min`;
    }
    if (rule.action_type === 'preferred_machine' && rule.action_value) {
      const machine = machines.find(m => m.id === rule.action_value);
      return `Préférée: ${machine?.name || rule.action_value}`;
    }
    return actionTypes.find(a => a.value === rule.action_type)?.label || rule.action_type;
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="text-2xl font-semibold text-slate-800">Règles Métier</h3>
        <button
          data-testid="create-rule-btn"
          onClick={() => setShowForm(!showForm)}
          className="inline-flex items-center gap-2 bg-slate-900 text-white hover:bg-slate-800 rounded-sm px-4 py-2 text-sm font-medium transition-colors shadow-sm"
        >
          <Plus size={16} />
          Nouvelle Règle
        </button>
      </div>

      {showForm && (
        <div className="bg-white border border-slate-200 rounded-sm shadow-sm p-5">
          <h4 className="text-lg font-semibold text-slate-800 mb-4">Nouvelle Règle Métier</h4>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-xs font-semibold uppercase tracking-wider text-slate-500 block mb-2">
                  Nom de la règle *
                </label>
                <input
                  data-testid="rule-name-input"
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full h-9 rounded-sm border border-slate-300 bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus:outline-none focus:ring-1 focus:ring-slate-900"
                  required
                />
              </div>
              <div>
                <label className="text-xs font-semibold uppercase tracking-wider text-slate-500 block mb-2">
                  Type de règle
                </label>
                <select
                  value={formData.rule_type}
                  onChange={(e) => setFormData({ ...formData, rule_type: e.target.value })}
                  className="w-full h-9 rounded-sm border border-slate-300 bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus:outline-none focus:ring-1 focus:ring-slate-900"
                >
                  {ruleTypes.map((type) => (
                    <option key={type.value} value={type.value}>
                      {type.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="bg-blue-50 border border-blue-200 rounded-sm p-4">
              <p className="text-sm font-semibold text-blue-900 mb-2">Critères de Ciblage</p>
              <p className="text-xs text-blue-700 mb-3">Au moins un critère doit être défini</p>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-xs font-semibold text-blue-700 block mb-1">
                    Task ID
                  </label>
                  <input
                    data-testid="task-id-input"
                    type="text"
                    value={formData.task_id}
                    onChange={(e) => setFormData({ ...formData, task_id: e.target.value })}
                    placeholder="Ex: USINAGE, ASSEMBLAGE"
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
                    Machine ID (optionnel)
                  </label>
                  <select
                    value={formData.machine_id}
                    onChange={(e) => setFormData({ ...formData, machine_id: e.target.value })}
                    className="w-full h-9 rounded-sm border border-blue-300 bg-white px-3 py-1 text-sm shadow-sm transition-colors focus:outline-none focus:ring-1 focus:ring-blue-600"
                  >
                    <option value="">Aucune machine spécifique</option>
                    {machines.map((machine) => (
                      <option key={machine.id} value={machine.id}>
                        {machine.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-xs font-semibold text-blue-700 block mb-1">
                    Article ID (optionnel)
                  </label>
                  <input
                    type="text"
                    value={formData.article_id}
                    onChange={(e) => setFormData({ ...formData, article_id: e.target.value })}
                    placeholder="Ex: ART001"
                    className="w-full h-9 rounded-sm border border-blue-300 bg-white px-3 py-1 text-sm shadow-sm transition-colors focus:outline-none focus:ring-1 focus:ring-blue-600"
                  />
                </div>
              </div>
            </div>

            <div className="bg-amber-50 border border-amber-200 rounded-sm p-4">
              <p className="text-sm font-semibold text-amber-900 mb-2">Action</p>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-xs font-semibold text-amber-700 block mb-1">
                    Type d'action *
                  </label>
                  <select
                    data-testid="action-type-select"
                    value={formData.action_type}
                    onChange={(e) => setFormData({ ...formData, action_type: e.target.value })}
                    className="w-full h-9 rounded-sm border border-amber-300 bg-white px-3 py-1 text-sm shadow-sm transition-colors focus:outline-none focus:ring-1 focus:ring-amber-600"
                  >
                    {actionTypes.map((type) => (
                      <option key={type.value} value={type.value}>
                        {type.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-xs font-semibold text-amber-700 block mb-1">
                    Valeur
                  </label>
                  {formData.action_type === 'preferred_machine' ? (
                    <select
                      data-testid="action-value-machine-select"
                      value={formData.action_value}
                      onChange={(e) => setFormData({ ...formData, action_value: e.target.value })}
                      className="w-full h-9 rounded-sm border border-amber-300 bg-white px-3 py-1 text-sm shadow-sm transition-colors focus:outline-none focus:ring-1 focus:ring-amber-600"
                    >
                      <option value="">Sélectionner machine</option>
                      {machines.map((machine) => (
                        <option key={machine.id} value={machine.id}>
                          {machine.name}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <input
                      data-testid="action-value-input"
                      type="text"
                      value={formData.action_value}
                      onChange={(e) => setFormData({ ...formData, action_value: e.target.value })}
                      placeholder={formData.action_type === 'penalty' ? 'Ex: 100' : formData.action_type === 'setup_time' ? 'Minutes' : ''}
                      className="w-full h-9 rounded-sm border border-amber-300 bg-white px-3 py-1 text-sm shadow-sm transition-colors focus:outline-none focus:ring-1 focus:ring-amber-600"
                    />
                  )}
                </div>
              </div>
              <div className="mt-3">
                <label className="flex items-center gap-2 text-sm text-amber-800">
                  <input
                    type="checkbox"
                    checked={formData.is_hard}
                    onChange={(e) => setFormData({ ...formData, is_hard: e.target.checked })}
                    className="rounded border-amber-300"
                  />
                  Règle dure (bloquante)
                </label>
              </div>
            </div>

            <div>
              <label className="text-xs font-semibold uppercase tracking-wider text-slate-500 block mb-2">
                Description
              </label>
              <textarea
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                className="w-full rounded-sm border border-slate-300 bg-transparent px-3 py-2 text-sm shadow-sm transition-colors focus:outline-none focus:ring-1 focus:ring-slate-900"
                rows={2}
                placeholder="Description optionnelle de la règle"
              />
            </div>

            <div className="flex gap-2">
              <button
                type="submit"
                data-testid="submit-rule-btn"
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
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Critères</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Action</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Type</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Actif</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody>
            {rules.map((rule) => (
              <tr key={rule.id} className="border-b border-slate-100 hover:bg-slate-50 transition-colors" data-testid="rule-row">
                <td className="px-4 py-2 text-sm text-slate-900 font-medium">{rule.name}</td>
                <td className="px-4 py-2 text-xs text-slate-700 font-mono">{getRuleSummary(rule)}</td>
                <td className="px-4 py-2 text-sm text-slate-700">{getActionSummary(rule)}</td>
                <td className="px-4 py-2">
                  <span
                    className={`px-2 py-0.5 rounded text-xs ${
                      rule.is_hard ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700'
                    }`}
                  >
                    {rule.is_hard ? 'Dure' : 'Souple'}
                  </span>
                </td>
                <td className="px-4 py-2">
                  <span
                    className={`px-2 py-0.5 rounded text-xs ${
                      rule.active ? 'bg-green-100 text-green-700' : 'bg-slate-100 text-slate-500'
                    }`}
                  >
                    {rule.active ? 'Oui' : 'Non'}
                  </span>
                </td>
                <td className="px-4 py-2">
                  <button
                    data-testid="delete-rule-btn"
                    onClick={() => handleDelete(rule.id)}
                    className="text-red-600 hover:text-red-800 transition-colors"
                  >
                    <Trash2 size={16} />
                  </button>
                </td>
              </tr>
            ))}
            {rules.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-sm text-slate-500">
                  Aucune règle. Cliquez sur "Nouvelle Règle" pour en créer une.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="bg-slate-50 border border-slate-200 rounded-sm p-5">
        <h4 className="text-lg font-semibold text-slate-800 mb-3">Exemples de Règles</h4>
        <div className="space-y-2 text-sm text-slate-700">
          <div className="flex items-start gap-2">
            <span className="font-mono text-slate-900">•</span>
            <p><strong>Task USINAGE interdit sur machine M001</strong>: task_id=USINAGE, machine_id=M001, action=forbid, is_hard=true</p>
          </div>
          <div className="flex items-start gap-2">
            <span className="font-mono text-slate-900">•</span>
            <p><strong>Task ASSEMBLAGE autorisé seulement sur WC002</strong>: task_id=ASSEMBLAGE, work_center_id=WC002, action=allow</p>
          </div>
          <div className="flex items-start gap-2">
            <span className="font-mono text-slate-900">•</span>
            <p><strong>Task + WC => temps de réglage +30min</strong>: task_id=USINAGE, work_center_id=WC001, action=setup_time, value=30</p>
          </div>
          <div className="flex items-start gap-2">
            <span className="font-mono text-slate-900">•</span>
            <p><strong>Machine préférée pour task</strong>: task_id=USINAGE, work_center_id=WC001, action=preferred_machine, value=machine_id</p>
          </div>
        </div>
      </div>
    </div>
  );
}
