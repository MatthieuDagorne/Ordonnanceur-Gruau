import { useEffect, useState } from 'react';
import axios from 'axios';
import { Plus, Trash2 } from 'lucide-react';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function BusinessRules() {
  const [rules, setRules] = useState([]);
  const [machines, setMachines] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({
    rule_type: 'machine_operation',
    is_hard: true,
    machine_id: '',
    operation_code: '',
    article_id: '',
    allowed: true,
    penalty: 0,
    setup_time_minutes: null,
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
      await axios.post(`${API}/rules`, formData);
      toast.success('Règle créée');
      setFormData({
        rule_type: 'machine_operation',
        is_hard: true,
        machine_id: '',
        operation_code: '',
        article_id: '',
        allowed: true,
        penalty: 0,
        setup_time_minutes: null,
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

  const ruleTypes = [
    { value: 'machine_operation', label: 'Machine / Opération' },
    { value: 'article_machine', label: 'Article / Machine' },
    { value: 'preference', label: 'Préférence Machine' },
  ];

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
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="text-xs font-semibold uppercase tracking-wider text-slate-500 block mb-2">
                Type de règle
              </label>
              <select
                data-testid="rule-type-select"
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
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-xs font-semibold uppercase tracking-wider text-slate-500 block mb-2">
                  Contrainte dure
                </label>
                <select
                  data-testid="is-hard-select"
                  value={formData.is_hard.toString()}
                  onChange={(e) => setFormData({ ...formData, is_hard: e.target.value === 'true' })}
                  className="w-full h-9 rounded-sm border border-slate-300 bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus:outline-none focus:ring-1 focus:ring-slate-900"
                >
                  <option value="true">Oui (interdite)</option>
                  <option value="false">Non (pénalité)</option>
                </select>
              </div>
              <div>
                <label className="text-xs font-semibold uppercase tracking-wider text-slate-500 block mb-2">
                  Autorisé
                </label>
                <select
                  data-testid="allowed-select"
                  value={formData.allowed.toString()}
                  onChange={(e) => setFormData({ ...formData, allowed: e.target.value === 'true' })}
                  className="w-full h-9 rounded-sm border border-slate-300 bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus:outline-none focus:ring-1 focus:ring-slate-900"
                >
                  <option value="true">Oui</option>
                  <option value="false">Non</option>
                </select>
              </div>
            </div>
            <div>
              <label className="text-xs font-semibold uppercase tracking-wider text-slate-500 block mb-2">
                Machine
              </label>
              <select
                data-testid="rule-machine-select"
                value={formData.machine_id}
                onChange={(e) => setFormData({ ...formData, machine_id: e.target.value })}
                className="w-full h-9 rounded-sm border border-slate-300 bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus:outline-none focus:ring-1 focus:ring-slate-900"
              >
                <option value="">Sélectionner une machine</option>
                {machines.map((machine) => (
                  <option key={machine.id} value={machine.id}>
                    {machine.name}
                  </option>
                ))}
              </select>
            </div>
            {(formData.rule_type === 'machine_operation' || formData.rule_type === 'preference') && (
              <div>
                <label className="text-xs font-semibold uppercase tracking-wider text-slate-500 block mb-2">
                  Code opération
                </label>
                <input
                  data-testid="operation-code-input"
                  type="text"
                  value={formData.operation_code}
                  onChange={(e) => setFormData({ ...formData, operation_code: e.target.value })}
                  className="w-full h-9 rounded-sm border border-slate-300 bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus:outline-none focus:ring-1 focus:ring-slate-900"
                />
              </div>
            )}
            {formData.rule_type === 'article_machine' && (
              <div>
                <label className="text-xs font-semibold uppercase tracking-wider text-slate-500 block mb-2">
                  ID Article
                </label>
                <input
                  data-testid="article-id-input"
                  type="text"
                  value={formData.article_id}
                  onChange={(e) => setFormData({ ...formData, article_id: e.target.value })}
                  className="w-full h-9 rounded-sm border border-slate-300 bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus:outline-none focus:ring-1 focus:ring-slate-900"
                />
              </div>
            )}
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
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Type</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Dure</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Machine</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Détails</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Autorisé</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody>
            {rules.map((rule) => {
              const machine = machines.find((m) => m.id === rule.machine_id);
              return (
                <tr key={rule.id} className="border-b border-slate-100 hover:bg-slate-50 transition-colors" data-testid="rule-row">
                  <td className="px-4 py-2 text-sm text-slate-700">{rule.rule_type}</td>
                  <td className="px-4 py-2 text-sm text-slate-700">
                    <span
                      className={`px-2 py-0.5 rounded text-xs ${
                        rule.is_hard ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700'
                      }`}
                    >
                      {rule.is_hard ? 'Oui' : 'Non'}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-sm text-slate-700 font-mono">{machine?.name || rule.machine_id || '-'}</td>
                  <td className="px-4 py-2 text-sm text-slate-700 font-mono">
                    {rule.operation_code || rule.article_id || '-'}
                  </td>
                  <td className="px-4 py-2 text-sm text-slate-700">
                    <span
                      className={`px-2 py-0.5 rounded text-xs ${
                        rule.allowed ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                      }`}
                    >
                      {rule.allowed ? 'Oui' : 'Non'}
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
              );
            })}
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
    </div>
  );
}