import { useEffect, useState, useMemo } from 'react';
import axios from 'axios';
import { Plus, Trash2, CheckCircle, Ban, Star, AlertCircle, Pencil, X, PlusCircle, MinusCircle, Filter, Search } from 'lucide-react';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const RULE_TYPES = [
  { value: 'REQUIRE', label: 'Requis - Exclusif', icon: CheckCircle, color: 'text-green-600', bg: 'bg-green-100', description: 'Seule cette machine peut traiter' },
  { value: 'FORBID', label: 'Interdit', icon: Ban, color: 'text-red-600', bg: 'bg-red-100', description: 'Cette machine est interdite' },
  { value: 'PREFER', label: 'Préféré', icon: Star, color: 'text-amber-600', bg: 'bg-amber-100', description: 'Préférence (non contraignant)' }
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

const EMPTY_CONDITION = { attribute_name: '', operator: 'GT', value: '' };
const EMPTY_GROUP = { conditions: [{ ...EMPTY_CONDITION }], logic: 'AND' };

export default function BusinessRules() {
  const [rules, setRules] = useState([]);
  const [machines, setMachines] = useState([]);
  const [centres, setCentres] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [editingRule, setEditingRule] = useState(null);
  const [ruleMode, setRuleMode] = useState('simple');
  
  // Filtres
  const [filters, setFilters] = useState({
    search: '',
    machine_id: '',
    rule_type: '',
    centre_de_charge_id: '',
    active: ''
  });
  const [showFilters, setShowFilters] = useState(false);
  
  // Formulaire de base
  const [formData, setFormData] = useState({
    name: '',
    tache_id: '',
    centre_de_charge_id: '',
    article_id: '',
    rule_type: 'REQUIRE',
    machine_id: '',
    active: true
  });
  
  // Conditions multiples sur attributs
  const [conditionGroups, setConditionGroups] = useState([{ ...EMPTY_GROUP }]);
  const [conditionsLogic, setConditionsLogic] = useState('AND'); // Entre les groupes
  
  const [formError, setFormError] = useState('');

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [rulesRes, machinesRes, centresRes] = await Promise.all([
        axios.get(`${API}/rules`),
        axios.get(`${API}/machines`),
        axios.get(`${API}/centres-de-charge`)
      ]);
      setRules(rulesRes.data);
      setMachines(machinesRes.data);
      setCentres(centresRes.data);
    } catch (error) {
      console.error('Error:', error);
      toast.error('Erreur lors du chargement');
    }
  };

  // Filtrage des règles
  const filteredRules = useMemo(() => {
    return rules.filter(rule => {
      // Recherche textuelle
      if (filters.search) {
        const searchLower = filters.search.toLowerCase();
        const matchName = String(rule.name || '').toLowerCase().includes(searchLower);
        const matchMachine = String(rule.machine_id || '').toLowerCase().includes(searchLower);
        const matchArticle = String(rule.article_id || '').toLowerCase().includes(searchLower);
        if (!matchName && !matchMachine && !matchArticle) return false;
      }
      
      // Filtre par machine
      if (filters.machine_id && rule.machine_id !== filters.machine_id) return false;
      
      // Filtre par type
      if (filters.rule_type && rule.rule_type !== filters.rule_type) return false;
      
      // Filtre par centre
      if (filters.centre_de_charge_id && rule.centre_de_charge_id !== filters.centre_de_charge_id) return false;
      
      // Filtre par état
      if (filters.active === 'true' && !rule.active) return false;
      if (filters.active === 'false' && rule.active) return false;
      
      return true;
    });
  }, [rules, filters]);

  const clearFilters = () => {
    setFilters({ search: '', machine_id: '', rule_type: '', centre_de_charge_id: '', active: '' });
  };

  const activeFiltersCount = Object.values(filters).filter(v => v !== '').length;

  // === Gestion des conditions ===
  const addConditionGroup = () => {
    setConditionGroups([...conditionGroups, { conditions: [{ ...EMPTY_CONDITION }], logic: 'AND' }]);
  };

  const removeConditionGroup = (groupIndex) => {
    if (conditionGroups.length > 1) {
      setConditionGroups(conditionGroups.filter((_, i) => i !== groupIndex));
    }
  };

  const addConditionToGroup = (groupIndex) => {
    const newGroups = [...conditionGroups];
    newGroups[groupIndex].conditions.push({ ...EMPTY_CONDITION });
    setConditionGroups(newGroups);
  };

  const removeConditionFromGroup = (groupIndex, conditionIndex) => {
    const newGroups = [...conditionGroups];
    if (newGroups[groupIndex].conditions.length > 1) {
      newGroups[groupIndex].conditions = newGroups[groupIndex].conditions.filter((_, i) => i !== conditionIndex);
      setConditionGroups(newGroups);
    }
  };

  const updateCondition = (groupIndex, conditionIndex, field, value) => {
    const newGroups = [...conditionGroups];
    newGroups[groupIndex].conditions[conditionIndex][field] = value;
    setConditionGroups(newGroups);
  };

  const updateGroupLogic = (groupIndex, logic) => {
    const newGroups = [...conditionGroups];
    newGroups[groupIndex].logic = logic;
    setConditionGroups(newGroups);
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
      if (!formData.tache_id && !formData.article_id) {
        setFormError('Au moins un critère simple (tâche ou article) doit être défini');
        return false;
      }
    } else {
      // Vérifier qu'au moins une condition est complète
      let hasValidCondition = false;
      for (const group of conditionGroups) {
        for (const cond of group.conditions) {
          if (cond.attribute_name && cond.operator && cond.value) {
            hasValidCondition = true;
            break;
          }
        }
        if (hasValidCondition) break;
      }
      
      if (!hasValidCondition) {
        setFormError('Au moins une condition complète (attribut + opérateur + valeur) est requise');
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
      
      // Conditions sur attributs
      if (ruleMode === 'attribute') {
        // Filtrer les conditions vides et formater
        const validGroups = conditionGroups
          .map(group => ({
            conditions: group.conditions.filter(c => c.attribute_name && c.operator && c.value),
            logic: group.logic
          }))
          .filter(group => group.conditions.length > 0);
        
        if (validGroups.length > 0) {
          cleanData.attribute_conditions = validGroups;
          cleanData.conditions_logic = conditionsLogic;
        }
      }

      if (editingRule) {
        const response = await axios.put(`${API}/rules/${editingRule.id}`, cleanData);
        setRules(rules.map(r => r.id === editingRule.id ? response.data : r));
        toast.success(`Règle "${response.data.name}" mise à jour`);
      } else {
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
    // Déterminer le mode
    const hasMultipleConditions = rule.attribute_conditions && rule.attribute_conditions.length > 0;
    const hasSingleAttribute = rule.attribute_name && rule.attribute_operator;
    
    if (hasMultipleConditions) {
      setRuleMode('attribute');
      setConditionGroups(rule.attribute_conditions.map(g => ({
        conditions: g.conditions || [],
        logic: g.logic || 'AND'
      })));
      setConditionsLogic(rule.conditions_logic || 'AND');
    } else if (hasSingleAttribute) {
      setRuleMode('attribute');
      setConditionGroups([{
        conditions: [{
          attribute_name: rule.attribute_name,
          operator: rule.attribute_operator,
          value: rule.attribute_value
        }],
        logic: 'AND'
      }]);
      setConditionsLogic('AND');
    } else {
      setRuleMode('simple');
      setConditionGroups([{ ...EMPTY_GROUP }]);
      setConditionsLogic('AND');
    }
    
    setFormData({
      name: rule.name || '',
      tache_id: rule.tache_id || '',
      centre_de_charge_id: rule.centre_de_charge_id || '',
      article_id: rule.article_id || '',
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
      rule_type: 'REQUIRE',
      machine_id: '',
      active: true
    });
    setConditionGroups([{ conditions: [{ ...EMPTY_CONDITION }], logic: 'AND' }]);
    setConditionsLogic('AND');
    setShowForm(false);
    setEditingRule(null);
    setFormError('');
    setRuleMode('simple');
  };

  const handleDelete = async (ruleId, ruleName) => {
    if (!window.confirm(`Supprimer la règle "${ruleName}" ?`)) return;
    
    try {
      await axios.delete(`${API}/rules/${ruleId}`);
      setRules(rules.filter(r => r.id !== ruleId));
      toast.success(`Règle "${ruleName}" supprimée`);
    } catch (error) {
      toast.error('Erreur lors de la suppression');
    }
  };

  const getRuleTypeDisplay = (ruleType) => {
    const type = RULE_TYPES.find(t => t.value === ruleType);
    if (!type) return { icon: AlertCircle, color: 'text-slate-500', bg: 'bg-slate-100' };
    return type;
  };

  // Fonction pour afficher les conditions d'une règle
  const renderRuleConditions = (rule) => {
    const parts = [];
    
    if (rule.tache_id) parts.push(`tâche=${rule.tache_id}`);
    if (rule.centre_de_charge_id) parts.push(`centre=${rule.centre_de_charge_id}`);
    if (rule.article_id) parts.push(`article=${rule.article_id}`);
    
    // Conditions multiples
    if (rule.attribute_conditions && rule.attribute_conditions.length > 0) {
      const groupsDisplay = rule.attribute_conditions.map((group, gi) => {
        const conditions = group.conditions || [];
        const logic = group.logic || 'AND';
        
        const condParts = conditions.map(cond => {
          const opDisplay = { GT: '>', GE: '>=', LT: '<', LE: '<=', EQ: '=', NE: '!=', IN: 'dans', NOT_IN: '∉' }[cond.operator] || cond.operator;
          return `${cond.attribute_name} ${opDisplay} ${cond.value}`;
        });
        
        const joiner = logic === 'AND' ? ' ET ' : ' OU ';
        return condParts.length > 1 ? `(${condParts.join(joiner)})` : condParts[0];
      });
      
      const mainJoiner = rule.conditions_logic === 'OR' ? ' OU ' : ' ET ';
      parts.push(groupsDisplay.join(mainJoiner));
    }
    // Attribut unique (rétro-compatibilité)
    else if (rule.attribute_name && rule.attribute_operator) {
      const opDisplay = { GT: '>', GE: '>=', LT: '<', LE: '<=', EQ: '=', NE: '!=', IN: 'dans', NOT_IN: '∉' }[rule.attribute_operator] || rule.attribute_operator;
      parts.push(`${rule.attribute_name} ${opDisplay} ${rule.attribute_value}`);
    }
    
    return parts.join(' + ') || 'Aucun critère';
  };

  return (
    <div className="space-y-6" data-testid="business-rules-page">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-2xl font-semibold" style={{ color: 'var(--text-primary)' }}>Règles Métier</h3>
          <p className="text-sm mt-1" style={{ color: 'var(--text-secondary)' }}>
            Règles d'affectation machine avec conditions ET/OU sur attributs
          </p>
        </div>
        <button
          onClick={() => { resetForm(); setShowForm(true); }}
          className="inline-flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium"
          style={{ backgroundColor: 'var(--brand-primary)', color: 'white' }}
          data-testid="new-rule-btn"
        >
          <Plus size={16} />
          Nouvelle Règle
        </button>
      </div>

      {/* Barre de filtres */}
      <div className="rounded-lg p-4" style={{ backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--border-default)' }}>
        <div className="flex items-center gap-4">
          {/* Recherche */}
          <div className="flex-1 relative">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: 'var(--text-muted)' }} />
            <input
              type="text"
              placeholder="Rechercher par nom, machine, article..."
              value={filters.search}
              onChange={(e) => setFilters({ ...filters, search: e.target.value })}
              className="w-full h-9 pl-9 pr-3 rounded-lg border text-sm"
              style={{ backgroundColor: 'var(--bg-sunken)', borderColor: 'var(--border-default)', color: 'var(--text-primary)' }}
              data-testid="filter-search"
            />
          </div>
          
          {/* Toggle filtres avancés */}
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`inline-flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${activeFiltersCount > 0 ? '' : ''}`}
            style={{ 
              backgroundColor: activeFiltersCount > 0 ? 'var(--status-info-bg)' : 'var(--bg-sunken)', 
              color: activeFiltersCount > 0 ? 'var(--status-info)' : 'var(--text-secondary)',
              border: '1px solid var(--border-default)'
            }}
            data-testid="toggle-filters"
          >
            <Filter size={16} />
            Filtres {activeFiltersCount > 0 && `(${activeFiltersCount})`}
          </button>
          
          {activeFiltersCount > 0 && (
            <button
              onClick={clearFilters}
              className="text-sm font-medium transition-colors"
              style={{ color: 'var(--status-error)' }}
              data-testid="clear-filters"
            >
              Réinitialiser
            </button>
          )}
        </div>
        
        {/* Filtres avancés */}
        {showFilters && (
          <div className="grid grid-cols-4 gap-4 mt-4 pt-4" style={{ borderTop: '1px solid var(--border-default)' }}>
            <div>
              <label className="text-xs font-semibold uppercase tracking-wider block mb-1" style={{ color: 'var(--text-muted)' }}>Machine</label>
              <select
                value={filters.machine_id}
                onChange={(e) => setFilters({ ...filters, machine_id: e.target.value })}
                className="w-full h-9 rounded-lg border px-2 text-sm"
                style={{ backgroundColor: 'var(--bg-sunken)', borderColor: 'var(--border-default)', color: 'var(--text-primary)' }}
                data-testid="filter-machine"
              >
                <option value="">Toutes</option>
                {machines.map(m => (
                  <option key={m.id} value={m.id}>{m.id}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs font-semibold uppercase tracking-wider block mb-1" style={{ color: 'var(--text-muted)' }}>Type</label>
              <select
                value={filters.rule_type}
                onChange={(e) => setFilters({ ...filters, rule_type: e.target.value })}
                className="w-full h-9 rounded-lg border px-2 text-sm"
                style={{ backgroundColor: 'var(--bg-sunken)', borderColor: 'var(--border-default)', color: 'var(--text-primary)' }}
                data-testid="filter-type"
              >
                <option value="">Tous</option>
                <option value="REQUIRE">Requis</option>
                <option value="FORBID">Interdit</option>
                <option value="PREFER">Préféré</option>
              </select>
            </div>
            <div>
              <label className="text-xs font-semibold uppercase tracking-wider block mb-1" style={{ color: 'var(--text-muted)' }}>Centre</label>
              <select
                value={filters.centre_de_charge_id}
                onChange={(e) => setFilters({ ...filters, centre_de_charge_id: e.target.value })}
                className="w-full h-9 rounded-lg border px-2 text-sm"
                style={{ backgroundColor: 'var(--bg-sunken)', borderColor: 'var(--border-default)', color: 'var(--text-primary)' }}
                data-testid="filter-centre"
              >
                <option value="">Tous</option>
                {centres.map(c => (
                  <option key={c.id} value={c.id}>{c.id}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs font-semibold uppercase tracking-wider block mb-1" style={{ color: 'var(--text-muted)' }}>État</label>
              <select
                value={filters.active}
                onChange={(e) => setFilters({ ...filters, active: e.target.value })}
                className="w-full h-9 rounded-lg border px-2 text-sm"
                style={{ backgroundColor: 'var(--bg-sunken)', borderColor: 'var(--border-default)', color: 'var(--text-primary)' }}
                data-testid="filter-active"
              >
                <option value="">Tous</option>
                <option value="true">Actif</option>
                <option value="false">Inactif</option>
              </select>
            </div>
          </div>
        )}
        
        {/* Compteur de résultats */}
        <div className="mt-3 text-sm" style={{ color: 'var(--text-muted)' }}>
          {filteredRules.length} règle(s) sur {rules.length}
        </div>
      </div>

      {showForm && (
        <div className="bg-white border border-slate-200 rounded-lg shadow-sm p-5" data-testid="rule-form">
          <div className="flex items-center justify-between mb-4">
            <h4 className="text-lg font-semibold text-slate-800">
              {editingRule ? `Modifier la règle "${editingRule.name}"` : 'Nouvelle Règle d\'Affectation'}
            </h4>
            <button onClick={resetForm} className="text-slate-400 hover:text-slate-600" data-testid="close-form-btn">
              <X size={20} />
            </button>
          </div>
          
          {formError && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-red-700 text-sm">
              <AlertCircle size={16} />
              {formError}
            </div>
          )}
          
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Nom et Machine */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-xs font-semibold uppercase tracking-wider text-slate-500">Nom *</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="mt-1 w-full h-10 rounded-lg border border-slate-300 bg-transparent px-3 text-sm"
                  placeholder="Ex: Interdiction largeur > 5000mm"
                  data-testid="rule-name-input"
                />
              </div>
              <div>
                <label className="text-xs font-semibold uppercase tracking-wider text-slate-500">Machine Cible *</label>
                <select
                  value={formData.machine_id}
                  onChange={(e) => setFormData({ ...formData, machine_id: e.target.value })}
                  className="mt-1 w-full h-10 rounded-lg border border-slate-300 bg-white px-3 text-sm"
                  data-testid="rule-machine-select"
                >
                  <option value="">-- Sélectionner --</option>
                  {machines.map(m => (
                    <option key={m.id} value={m.id}>{m.id} - {m.nom || m.name}</option>
                  ))}
                </select>
              </div>
            </div>

            {/* Type de règle */}
            <div>
              <label className="text-xs font-semibold uppercase tracking-wider text-slate-500">Type de Règle</label>
              <div className="mt-2 flex gap-3">
                {RULE_TYPES.map(type => {
                  const Icon = type.icon;
                  return (
                    <button
                      key={type.value}
                      type="button"
                      onClick={() => setFormData({ ...formData, rule_type: type.value })}
                      className={`flex items-center gap-2 px-4 py-2 rounded-lg border-2 transition-all ${
                        formData.rule_type === type.value
                          ? `border-slate-900 ${type.bg}`
                          : 'border-slate-200 hover:border-slate-300'
                      }`}
                      data-testid={`rule-type-${type.value}`}
                    >
                      <Icon size={16} className={type.color} />
                      <span className="text-sm font-medium">{type.value}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Mode de règle */}
            <div>
              <label className="text-xs font-semibold uppercase tracking-wider text-slate-500">Mode de Conditions</label>
              <div className="mt-2 flex gap-3">
                <button
                  type="button"
                  onClick={() => setRuleMode('simple')}
                  className={`px-4 py-2 rounded-lg border-2 text-sm font-medium transition-all ${
                    ruleMode === 'simple' ? 'border-slate-900 bg-slate-100' : 'border-slate-200 hover:border-slate-300'
                  }`}
                  data-testid="mode-simple"
                >
                  Simple (ID)
                </button>
                <button
                  type="button"
                  onClick={() => setRuleMode('attribute')}
                  className={`px-4 py-2 rounded-lg border-2 text-sm font-medium transition-all ${
                    ruleMode === 'attribute' ? 'border-slate-900 bg-slate-100' : 'border-slate-200 hover:border-slate-300'
                  }`}
                  data-testid="mode-attribute"
                >
                  Attributs (ET/OU)
                </button>
              </div>
            </div>

            {/* Critères simples */}
            {ruleMode === 'simple' && (
              <div className="p-4 bg-slate-50 rounded-lg border border-slate-200">
                <h5 className="text-sm font-semibold text-slate-700 mb-3">Critères Simples</h5>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-xs text-slate-500">Tâche</label>
                    <input
                      type="text"
                      value={formData.tache_id}
                      onChange={(e) => setFormData({ ...formData, tache_id: e.target.value })}
                      className="mt-1 w-full h-9 rounded-lg border border-slate-300 px-3 text-sm"
                      placeholder="LVT001"
                    />
                  </div>
                  <div>
                    <label className="text-xs text-slate-500">Article</label>
                    <input
                      type="text"
                      value={formData.article_id}
                      onChange={(e) => setFormData({ ...formData, article_id: e.target.value })}
                      className="mt-1 w-full h-9 rounded-lg border border-slate-300 px-3 text-sm"
                      placeholder="100235570"
                    />
                  </div>
                </div>
              </div>
            )}

            {/* Conditions sur attributs avec ET/OU */}
            {ruleMode === 'attribute' && (
              <div className="conditions-box">
                <div className="flex items-center justify-between mb-3">
                  <h5 className="conditions-box-title">Conditions sur Attributs</h5>
                  
                  {/* Logique entre groupes */}
                  {conditionGroups.length > 1 && (
                    <div className="flex items-center gap-2">
                      <span className="conditions-group-label">Entre groupes:</span>
                      <select
                        value={conditionsLogic}
                        onChange={(e) => setConditionsLogic(e.target.value)}
                        className="h-8 rounded-lg border px-2 text-xs font-medium"
                        data-testid="conditions-logic"
                      >
                        <option value="AND">ET (toutes)</option>
                        <option value="OR">OU (au moins une)</option>
                      </select>
                    </div>
                  )}
                </div>

                {/* Groupes de conditions */}
                <div className="space-y-4">
                  {conditionGroups.map((group, gi) => (
                    <div key={gi} className="conditions-group">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <span className="conditions-group-label">Groupe {gi + 1}</span>
                          {group.conditions.length > 1 && (
                            <select
                              value={group.logic}
                              onChange={(e) => updateGroupLogic(gi, e.target.value)}
                              className="h-6 rounded-lg border px-2 text-xs font-medium"
                              data-testid={`group-logic-${gi}`}
                            >
                              <option value="AND">ET</option>
                              <option value="OR">OU</option>
                            </select>
                          )}
                        </div>
                        <div className="flex items-center gap-1">
                          <button
                            type="button"
                            onClick={() => addConditionToGroup(gi)}
                            className="p-1 text-blue-600 hover:text-blue-800"
                            title="Ajouter une condition"
                          >
                            <PlusCircle size={18} />
                          </button>
                          {conditionGroups.length > 1 && (
                            <button
                              type="button"
                              onClick={() => removeConditionGroup(gi)}
                              className="p-1 text-red-500 hover:text-red-700"
                              title="Supprimer le groupe"
                            >
                              <Trash2 size={16} />
                            </button>
                          )}
                        </div>
                      </div>
                      
                      {/* Conditions du groupe */}
                      <div className="space-y-2">
                        {group.conditions.map((cond, ci) => (
                          <div key={ci} className="flex items-center gap-2">
                            {ci > 0 && (
                              <span className="text-xs font-medium text-blue-500 w-8">
                                {group.logic}
                              </span>
                            )}
                            <select
                              value={cond.attribute_name}
                              onChange={(e) => updateCondition(gi, ci, 'attribute_name', e.target.value)}
                              className="flex-1 h-9 rounded-lg border border-slate-300 bg-white px-2 text-sm"
                              data-testid={`attr-name-${gi}-${ci}`}
                            >
                              <option value="">Attribut...</option>
                              {ATTRIBUTE_NAMES.map(a => (
                                <option key={a.value} value={a.value}>{a.label}</option>
                              ))}
                            </select>
                            <select
                              value={cond.operator}
                              onChange={(e) => updateCondition(gi, ci, 'operator', e.target.value)}
                              className="w-40 h-9 rounded-lg border border-slate-300 bg-white px-2 text-sm"
                              data-testid={`attr-op-${gi}-${ci}`}
                            >
                              {OPERATORS.map(o => (
                                <option key={o.value} value={o.value}>{o.label}</option>
                              ))}
                            </select>
                            <input
                              type="text"
                              value={cond.value}
                              onChange={(e) => updateCondition(gi, ci, 'value', e.target.value)}
                              className="w-32 h-9 rounded-lg border border-slate-300 px-2 text-sm"
                              placeholder="Valeur"
                              data-testid={`attr-val-${gi}-${ci}`}
                            />
                            {group.conditions.length > 1 && (
                              <button
                                type="button"
                                onClick={() => removeConditionFromGroup(gi, ci)}
                                className="p-1 text-red-500 hover:text-red-700"
                              >
                                <MinusCircle size={16} />
                              </button>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>

                {/* Ajouter un groupe */}
                <button
                  type="button"
                  onClick={addConditionGroup}
                  className="conditions-add-btn mt-3 inline-flex items-center gap-1 text-sm font-medium"
                  data-testid="add-group-btn"
                >
                  <PlusCircle size={16} />
                  Ajouter un groupe de conditions ({conditionsLogic === 'AND' ? 'ET' : 'OU'})
                </button>
              </div>
            )}

            {/* Boutons */}
            <div className="flex gap-2">
              <button 
                type="submit" 
                className="bg-slate-900 text-white hover:bg-slate-800 rounded-lg px-4 py-2 text-sm font-medium"
                data-testid="submit-rule-btn"
              >
                {editingRule ? 'Mettre à jour' : 'Créer la règle'}
              </button>
              <button 
                type="button" 
                onClick={resetForm} 
                className="bg-white text-slate-700 border border-slate-300 hover:bg-slate-50 rounded-lg px-4 py-2 text-sm font-medium"
              >
                Annuler
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Liste des règles */}
      <div className="rounded-lg overflow-hidden" style={{ backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--border-default)' }}>
        <table className="min-w-full">
          <thead style={{ backgroundColor: 'var(--bg-sunken)' }}>
            <tr>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase" style={{ color: 'var(--text-muted)' }}>Nom</th>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase" style={{ color: 'var(--text-muted)' }}>Type</th>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase" style={{ color: 'var(--text-muted)' }}>Conditions</th>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase" style={{ color: 'var(--text-muted)' }}>Machine</th>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase" style={{ color: 'var(--text-muted)' }}>État</th>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase" style={{ color: 'var(--text-muted)' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {filteredRules.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-sm" style={{ color: 'var(--text-muted)' }}>
                  {rules.length === 0 
                    ? 'Aucune règle métier. Cliquez sur "Nouvelle Règle" pour en créer une.'
                    : 'Aucune règle ne correspond aux filtres.'}
                </td>
              </tr>
            ) : (
              filteredRules.map((rule) => {
                const typeInfo = getRuleTypeDisplay(rule.rule_type);
                const Icon = typeInfo.icon;
                
                return (
                  <tr key={rule.id} className="transition-colors" style={{ borderBottom: '1px solid var(--border-default)' }}>
                    <td className="px-4 py-3">
                      <span className="font-medium" style={{ color: 'var(--text-primary)' }}>{rule.name}</span>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-lg text-xs font-medium ${typeInfo.bg} ${typeInfo.color}`}>
                        <Icon size={12} />
                        {rule.rule_type}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-sm font-mono" style={{ color: 'var(--text-secondary)' }}>
                        {renderRuleConditions(rule)}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="font-mono text-sm" style={{ color: 'var(--text-primary)' }}>{rule.machine_id}</span>
                    </td>
                    <td className="px-4 py-3">
                      {rule.active ? (
                        <span className="inline-flex items-center gap-1 text-xs font-medium" style={{ color: 'var(--status-success)' }}>
                          <CheckCircle size={12} /> Actif
                        </span>
                      ) : (
                        <span className="text-xs" style={{ color: 'var(--text-muted)' }}>Inactif</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex gap-1">
                        <button
                          onClick={() => handleEdit(rule)}
                          className="p-1.5 rounded-lg transition-colors hover:bg-slate-100 dark:hover:bg-slate-800"
                          title="Modifier"
                          data-testid={`edit-rule-${rule.id}`}
                        >
                          <Pencil size={16} style={{ color: 'var(--text-secondary)' }} />
                        </button>
                        <button
                          onClick={() => handleDelete(rule.id, rule.name)}
                          className="p-1.5 rounded-lg transition-colors hover:bg-red-100 dark:hover:bg-red-900/30"
                          title="Supprimer"
                          data-testid={`delete-rule-${rule.id}`}
                        >
                          <Trash2 size={16} className="text-red-600" />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
