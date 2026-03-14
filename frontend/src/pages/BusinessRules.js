import { useEffect, useState } from 'react';
import axios from 'axios';
import { Plus, Trash2, CheckCircle, Ban, Star, AlertCircle, Filter, Ruler, Pencil, X } from 'lucide-react';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const RULE_TYPES = [
  { value: 'ALLOW', label: 'ALLOW - Autoriser', icon: CheckCircle, color: 'text-green-600', bg: 'bg-green-100' },
  { value: 'FORBID', label: 'FORBID - Interdire', icon: Ban, color: 'text-red-600', bg: 'bg-red-100' },
  { value: 'PREFER', label: 'PREFER - Préférer', icon: Star, color: 'text-amber-600', bg: 'bg-amber-100' }
];

const ATTRIBUTE_NAMES = [
  { value: 'width', label: 'Largeur (mm)' },
  { value: 'length', label: 'Longueur (mm)' },
  { value: 'thickness', label: 'Épaisseur (mm)' },
  { value: 'material_type', label: 'Type de matière' },
  { value: 'color', label: 'Couleur' }
];

const OPERATORS = [
  { value: 'GT', label: '> Supérieur à' },
  { value: 'GE', label: '>= Supérieur ou égal' },
  { value: 'LT', label: '< Inférieur à' },
  { value: 'LE', label: '<= Inférieur ou égal' },
  { value: 'EQ', label: '= Égal à' },
  { value: 'NE', label: '!= Différent de' },
  { value: 'IN', label: 'Dans la liste' },
  { value: 'NOT_IN', label: 'Pas dans la liste' }
];

export default function BusinessRules() {
  const [rules, setRules] = useState([]);
  const [machines, setMachines] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [editingRule, setEditingRule] = useState(null); // Règle en cours d'édition
  const [ruleMode, setRuleMode] = useState('simple');
  const [formData, setFormData] = useState({
    name: '',
    tache_id: '',
    centre_de_charge_id: '',
    article_id: '',
    attribute_name: '',
    attribute_operator: '',
    attribute_value: '',
    rule_type: 'FORBID',
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
    if (!formData.machine_id) {
      setFormError('La machine cible est obligatoire');
      return false;
    }
    if (!formData.name.trim()) {
      setFormError('Le nom de la règle est obligatoire');
      return false;
    }
    
    if (ruleMode === 'simple') {
      if (!formData.tache_id && !formData.centre_de_charge_id && !formData.article_id) {
        setFormError('Au moins un critère simple (tâche, centre ou article) doit être défini');
        return false;
      }
    } else {
      if (!formData.attribute_name || !formData.attribute_operator || !formData.attribute_value) {
        setFormError('Tous les champs attribut (nom, opérateur, valeur) sont obligatoires');
        return false;
      }
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
      
      // Critères simples
      if (formData.tache_id.trim()) cleanData.tache_id = formData.tache_id.trim();
      if (formData.centre_de_charge_id.trim()) cleanData.centre_de_charge_id = formData.centre_de_charge_id.trim();
      if (formData.article_id.trim()) cleanData.article_id = formData.article_id.trim();
      
      // Critères sur attributs
      if (ruleMode === 'attribute' && formData.attribute_name) {
        cleanData.attribute_name = formData.attribute_name;
        cleanData.attribute_operator = formData.attribute_operator;
        cleanData.attribute_value = formData.attribute_value;
      }

      if (editingRule) {
        // Mode édition - PUT
        const response = await axios.put(`${API}/rules/${editingRule.id}`, cleanData);
        setRules(rules.map(r => r.id === editingRule.id ? response.data : r));
        toast.success(`Règle "${response.data.name}" mise à jour`);
      } else {
        // Mode création - POST
        const response = await axios.post(`${API}/rules`, cleanData);
        setRules([...rules, response.data]);
        toast.success(`Règle "${response.data.name}" créée`);
      }
      
      resetForm();
    } catch (error) {
      toast.error(`Erreur: ${error.response?.data?.detail || error.message}`);
    }
  };

  const handleEdit = (rule) => {
    // Déterminer le mode (simple ou attribut)
    const hasAttribute = rule.attribute_name && rule.attribute_operator;
    setRuleMode(hasAttribute ? 'attribute' : 'simple');
    
    // Pré-remplir le formulaire
    setFormData({
      name: rule.name || '',
      tache_id: rule.tache_id || '',
      centre_de_charge_id: rule.centre_de_charge_id || '',
      article_id: rule.article_id || '',
      attribute_name: rule.attribute_name || '',
      attribute_operator: rule.attribute_operator || '',
      attribute_value: rule.attribute_value || '',
      rule_type: rule.rule_type || 'FORBID',
      machine_id: rule.machine_id || '',
      active: rule.active !== false
    });
    
    setEditingRule(rule);
    setShowForm(true);
    setFormError('');
  };

  const resetForm = () => {
    setFormData({
      name: '',
      tache_id: '',
      centre_de_charge_id: '',
      article_id: '',
      attribute_name: '',
      attribute_operator: '',
      attribute_value: '',
      rule_type: 'FORBID',
      machine_id: '',
      active: true
    });
    setShowForm(false);
    setEditingRule(null);
    setFormError('');
    setRuleMode('simple');
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

  const getOperatorLabel = (op) => {
    return OPERATORS.find(o => o.value === op)?.label || op;
  };

  const getAttributeLabel = (attr) => {
    return ATTRIBUTE_NAMES.find(a => a.value === attr)?.label || attr;
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-2xl font-semibold text-slate-800">Règles Métier</h3>
          <p className="text-sm text-slate-500 mt-1">
            Règles d'affectation machine basées sur article, tâche, centre ou caractéristiques
          </p>
        </div>
        <button
          onClick={() => { resetForm(); setShowForm(true); }}
          className="inline-flex items-center gap-2 bg-slate-900 text-white hover:bg-slate-800 rounded-sm px-4 py-2 text-sm font-medium"
          data-testid="new-rule-btn"
        >
          <Plus size={16} />
          Nouvelle Règle
        </button>
      </div>

      {showForm && (
        <div className="bg-white border border-slate-200 rounded-sm shadow-sm p-5" data-testid="rule-form">
          <div className="flex items-center justify-between mb-4">
            <h4 className="text-lg font-semibold text-slate-800">
              {editingRule ? `Modifier la règle "${editingRule.name}"` : 'Nouvelle Règle d\'Affectation'}
            </h4>
            <button 
              onClick={resetForm}
              className="text-slate-400 hover:text-slate-600"
              data-testid="close-form-btn"
            >
              <X size={20} />
            </button>
          </div>
          
          {formError && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-sm flex items-center gap-2 text-red-700 text-sm">
              <AlertCircle size={16} />
              {formError}
            </div>
          )}
          
          {/* Sélection du mode de règle */}
          <div className="mb-4 flex gap-2">
            <button
              type="button"
              onClick={() => setRuleMode('simple')}
              className={`flex items-center gap-2 px-4 py-2 rounded-sm text-sm font-medium ${
                ruleMode === 'simple' 
                  ? 'bg-blue-600 text-white' 
                  : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
              }`}
              data-testid="mode-simple-btn"
            >
              <Filter size={14} />
              Règle Simple (article, tâche, centre)
            </button>
            <button
              type="button"
              onClick={() => setRuleMode('attribute')}
              className={`flex items-center gap-2 px-4 py-2 rounded-sm text-sm font-medium ${
                ruleMode === 'attribute' 
                  ? 'bg-purple-600 text-white' 
                  : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
              }`}
              data-testid="mode-attribute-btn"
            >
              <Ruler size={14} />
              Règle sur Attribut (largeur, épaisseur...)
            </button>
          </div>
          
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-xs font-semibold uppercase tracking-wider text-slate-500 block mb-2">
                  Nom de la règle *
                </label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="Ex: Largeur max 5000mm sur TP5000_1"
                  className="w-full h-9 rounded-sm border border-slate-300 px-3 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-slate-900"
                  required
                  data-testid="rule-name-input"
                />
              </div>
              <div>
                <label className="text-xs font-semibold uppercase tracking-wider text-slate-500 block mb-2">
                  Type de règle *
                </label>
                <select
                  value={formData.rule_type}
                  onChange={(e) => setFormData({ ...formData, rule_type: e.target.value })}
                  className="w-full h-9 rounded-sm border border-slate-300 px-3 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-slate-900"
                  data-testid="rule-type-select"
                >
                  {RULE_TYPES.map(type => (
                    <option key={type.value} value={type.value}>{type.label}</option>
                  ))}
                </select>
              </div>
            </div>

            {/* Critères simples */}
            {ruleMode === 'simple' && (
              <div className="bg-blue-50 border border-blue-200 rounded-sm p-4">
                <p className="text-sm font-semibold text-blue-900 mb-3">Critères de Ciblage (codes métier)</p>
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <label className="text-xs font-semibold text-blue-700 block mb-1">Tâche ID</label>
                    <input
                      type="text"
                      value={formData.tache_id}
                      onChange={(e) => setFormData({ ...formData, tache_id: e.target.value.toUpperCase() })}
                      placeholder="Ex: PLIAGE, LVT001"
                      className="w-full h-9 rounded-sm border border-blue-300 bg-white px-3 py-1 text-sm"
                      data-testid="tache-id-input"
                    />
                  </div>
                  <div>
                    <label className="text-xs font-semibold text-blue-700 block mb-1">Centre de Charge ID</label>
                    <input
                      type="text"
                      value={formData.centre_de_charge_id}
                      onChange={(e) => setFormData({ ...formData, centre_de_charge_id: e.target.value.toUpperCase() })}
                      placeholder="Ex: PLI01, LVC001"
                      className="w-full h-9 rounded-sm border border-blue-300 bg-white px-3 py-1 text-sm"
                      data-testid="centre-id-input"
                    />
                  </div>
                  <div>
                    <label className="text-xs font-semibold text-blue-700 block mb-1">Article ID</label>
                    <input
                      type="text"
                      value={formData.article_id}
                      onChange={(e) => setFormData({ ...formData, article_id: e.target.value })}
                      placeholder="Ex: 100235570"
                      className="w-full h-9 rounded-sm border border-blue-300 bg-white px-3 py-1 text-sm"
                      data-testid="article-id-input"
                    />
                  </div>
                </div>
              </div>
            )}

            {/* Critères sur attributs */}
            {ruleMode === 'attribute' && (
              <div className="bg-purple-50 border border-purple-200 rounded-sm p-4">
                <p className="text-sm font-semibold text-purple-900 mb-3">Critères sur Caractéristiques Article</p>
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <label className="text-xs font-semibold text-purple-700 block mb-1">Attribut</label>
                    <select
                      value={formData.attribute_name}
                      onChange={(e) => setFormData({ ...formData, attribute_name: e.target.value })}
                      className="w-full h-9 rounded-sm border border-purple-300 bg-white px-3 py-1 text-sm"
                      data-testid="attribute-name-select"
                    >
                      <option value="">-- Sélectionner --</option>
                      {ATTRIBUTE_NAMES.map(attr => (
                        <option key={attr.value} value={attr.value}>{attr.label}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="text-xs font-semibold text-purple-700 block mb-1">Opérateur</label>
                    <select
                      value={formData.attribute_operator}
                      onChange={(e) => setFormData({ ...formData, attribute_operator: e.target.value })}
                      className="w-full h-9 rounded-sm border border-purple-300 bg-white px-3 py-1 text-sm"
                      data-testid="attribute-operator-select"
                    >
                      <option value="">-- Sélectionner --</option>
                      {OPERATORS.map(op => (
                        <option key={op.value} value={op.value}>{op.label}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="text-xs font-semibold text-purple-700 block mb-1">Valeur</label>
                    <input
                      type="text"
                      value={formData.attribute_value}
                      onChange={(e) => setFormData({ ...formData, attribute_value: e.target.value })}
                      placeholder="Ex: 5000, ACIER"
                      className="w-full h-9 rounded-sm border border-purple-300 bg-white px-3 py-1 text-sm"
                      data-testid="attribute-value-input"
                    />
                  </div>
                </div>
                <p className="text-xs text-purple-600 mt-2">
                  Exemple: largeur &gt; 5000mm, épaisseur &gt; 5mm, matière = ACIER
                </p>
                
                {/* Optionnel: ajouter aussi des critères simples */}
                <div className="mt-4 pt-4 border-t border-purple-200">
                  <p className="text-xs text-purple-700 mb-2">Optionnel: Restreindre à une tâche/centre spécifique</p>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <input
                        type="text"
                        value={formData.tache_id}
                        onChange={(e) => setFormData({ ...formData, tache_id: e.target.value.toUpperCase() })}
                        placeholder="Tâche ID (optionnel)"
                        className="w-full h-8 rounded-sm border border-purple-300 bg-white px-3 py-1 text-sm"
                      />
                    </div>
                    <div>
                      <input
                        type="text"
                        value={formData.centre_de_charge_id}
                        onChange={(e) => setFormData({ ...formData, centre_de_charge_id: e.target.value.toUpperCase() })}
                        placeholder="Centre ID (optionnel)"
                        className="w-full h-8 rounded-sm border border-purple-300 bg-white px-3 py-1 text-sm"
                      />
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Machine cible */}
            <div className="bg-amber-50 border border-amber-200 rounded-sm p-4">
              <label className="text-xs font-semibold text-amber-700 block mb-2">Machine Cible *</label>
              <select
                value={formData.machine_id}
                onChange={(e) => setFormData({ ...formData, machine_id: e.target.value })}
                className="w-full h-9 rounded-sm border border-amber-300 bg-white px-3 py-1 text-sm"
                required
                data-testid="machine-select"
              >
                <option value="">-- Sélectionner une machine --</option>
                {machines.map(m => (
                  <option key={m.id} value={m.id}>
                    {m.id} - {m.nom || m.name} ({m.centre_de_charge_id || m.work_center_id})
                  </option>
                ))}
              </select>
            </div>

            <div className="flex gap-2">
              <button 
                type="submit" 
                className="bg-slate-900 text-white hover:bg-slate-800 rounded-sm px-4 py-2 text-sm font-medium"
                data-testid="submit-rule-btn"
              >
                {editingRule ? 'Mettre à jour' : 'Créer la règle'}
              </button>
              <button 
                type="button" 
                onClick={resetForm} 
                className="bg-white text-slate-700 border border-slate-300 hover:bg-slate-50 rounded-sm px-4 py-2 text-sm font-medium"
              >
                Annuler
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Liste des règles */}
      <div className="bg-white border border-slate-200 rounded-sm shadow-sm overflow-hidden" data-testid="rules-table">
        <table className="w-full">
          <thead className="bg-slate-50 border-b border-slate-200">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase">Type</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase">Nom</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase">Critères</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase">Machine</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody>
            {rules.map((rule) => {
              const typeInfo = getRuleTypeInfo(rule.rule_type);
              const TypeIcon = typeInfo.icon;
              const hasAttribute = rule.attribute_name && rule.attribute_operator;
              
              return (
                <tr key={rule.id || rule.name} className="border-b border-slate-100 hover:bg-slate-50" data-testid={`rule-row-${rule.id}`}>
                  <td className="px-4 py-3">
                    <span className={`inline-flex items-center gap-1.5 px-2 py-1 rounded text-xs font-medium ${typeInfo.bg} ${typeInfo.color}`}>
                      <TypeIcon size={12} />
                      {rule.rule_type}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-slate-900 font-medium">{rule.name}</td>
                  <td className="px-4 py-3">
                    <div className="space-y-1 text-xs">
                      {rule.tache_id && (
                        <span className="inline-block bg-slate-100 text-slate-700 px-1.5 py-0.5 rounded mr-1">
                          tâche: {rule.tache_id}
                        </span>
                      )}
                      {rule.centre_de_charge_id && (
                        <span className="inline-block bg-slate-100 text-slate-700 px-1.5 py-0.5 rounded mr-1">
                          centre: {rule.centre_de_charge_id}
                        </span>
                      )}
                      {rule.article_id && (
                        <span className="inline-block bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded mr-1">
                          article: {rule.article_id}
                        </span>
                      )}
                      {hasAttribute && (
                        <span className="inline-block bg-purple-100 text-purple-700 px-1.5 py-0.5 rounded">
                          {getAttributeLabel(rule.attribute_name)} {getOperatorLabel(rule.attribute_operator).split(' ')[0]} {rule.attribute_value}
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <span className="bg-amber-100 text-amber-800 px-2 py-1 rounded text-xs font-mono font-semibold">
                      {rule.machine_id}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex gap-1">
                      <button
                        onClick={() => handleEdit(rule)}
                        className="text-slate-600 hover:text-slate-800 p-1"
                        title="Modifier"
                        data-testid={`edit-rule-${rule.id}`}
                      >
                        <Pencil size={16} />
                      </button>
                      <button
                        onClick={() => handleDelete(rule.id, rule.name)}
                        className="text-red-600 hover:text-red-800 p-1"
                        title="Supprimer"
                        data-testid={`delete-rule-${rule.id}`}
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
            {rules.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-sm text-slate-500">
                  Aucune règle définie. Créez des règles pour contrôler l'affectation des machines.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
