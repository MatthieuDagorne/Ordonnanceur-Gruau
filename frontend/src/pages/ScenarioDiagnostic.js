import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, AlertTriangle, CheckCircle, Clock, Package, Zap, ArrowRight, Info, FastForward, Rewind, Settings } from 'lucide-react';

const API_URL = process.env.REACT_APP_BACKEND_URL;

export default function ScenarioDiagnostic() {
  const { scenarioId } = useParams();
  const [scenario, setScenario] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('params');

  useEffect(() => {
    fetchScenario();
  }, [scenarioId]);

  const fetchScenario = async () => {
    try {
      const res = await fetch(`${API_URL}/api/scenarios/${scenarioId}`);
      if (res.ok) {
        const data = await res.json();
        setScenario(data);
      }
    } catch (err) {
      console.error('Erreur chargement scénario:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2" style={{ borderColor: 'var(--accent-primary)' }}></div>
      </div>
    );
  }

  if (!scenario) {
    return (
      <div className="p-6">
        <div className="text-center py-12" style={{ color: 'var(--text-muted)' }}>
          Scénario non trouvé
        </div>
      </div>
    );
  }

  const scheduleData = scenario.schedule_data || {};
  const priorityPropagation = scheduleData.priority_propagation || [];
  const urgentOrders = scheduleData.urgent_orders || [];
  const productions = scheduleData.productions || [];
  const materialDelayed = scheduleData.material_delayed || [];
  const unscheduledOps = scheduleData.unscheduled_operations || [];
  const diagnostics = scheduleData.diagnostics || {};
  const schedulingStrategy = scheduleData.scheduling_strategy || 'ASAP';
  const schedulingStart = scheduleData.scheduling_start;

  const tabs = [
    { id: 'params', label: 'Paramètres', icon: Settings, count: null },
    { id: 'priority', label: 'Priorités', icon: Zap, count: priorityPropagation.length },
    { id: 'material', label: 'Matière', icon: Package, count: materialDelayed.length },
    { id: 'productions', label: 'Productions', icon: CheckCircle, count: productions.length },
    { id: 'issues', label: 'Alertes', icon: AlertTriangle, count: unscheduledOps.length },
  ];

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link
          to={`/gantt/${scenarioId}`}
          className="p-2 rounded-lg hover:opacity-80 transition-opacity"
          style={{ backgroundColor: 'var(--bg-elevated)' }}
          data-testid="back-to-gantt"
        >
          <ArrowLeft size={20} style={{ color: 'var(--text-secondary)' }} />
        </Link>
        <div>
          <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
            Diagnostic - {scenario.name}
          </h1>
          <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
            Analyse détaillée des décisions du moteur d'ordonnancement
          </p>
        </div>
      </div>

      {/* Résumé */}
      <div className="grid grid-cols-4 gap-4">
        <div className="p-4 rounded-xl" style={{ backgroundColor: 'var(--bg-elevated)' }}>
          <div className="flex items-center gap-2 mb-2">
            <Zap size={16} className="text-yellow-500" />
            <span className="text-sm" style={{ color: 'var(--text-muted)' }}>OFs Urgents</span>
          </div>
          <div className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
            {urgentOrders.length}
          </div>
        </div>
        
        <div className="p-4 rounded-xl" style={{ backgroundColor: 'var(--bg-elevated)' }}>
          <div className="flex items-center gap-2 mb-2">
            <Clock size={16} className="text-blue-500" />
            <span className="text-sm" style={{ color: 'var(--text-muted)' }}>Reportés Matière</span>
          </div>
          <div className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
            {materialDelayed.length}
          </div>
        </div>
        
        <div className="p-4 rounded-xl" style={{ backgroundColor: 'var(--bg-elevated)' }}>
          <div className="flex items-center gap-2 mb-2">
            <Package size={16} className="text-green-500" />
            <span className="text-sm" style={{ color: 'var(--text-muted)' }}>Productions</span>
          </div>
          <div className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
            {productions.length}
          </div>
        </div>
        
        <div className="p-4 rounded-xl" style={{ backgroundColor: 'var(--bg-elevated)' }}>
          <div className="flex items-center gap-2 mb-2">
            <AlertTriangle size={16} className="text-red-500" />
            <span className="text-sm" style={{ color: 'var(--text-muted)' }}>Non Planifiées</span>
          </div>
          <div className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
            {unscheduledOps.length}
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b" style={{ borderColor: 'var(--border-default)' }}>
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 px-4 py-3 text-sm font-medium transition-colors border-b-2 -mb-px`}
            style={{
              borderColor: activeTab === tab.id ? 'var(--accent-primary)' : 'transparent',
              color: activeTab === tab.id ? 'var(--accent-primary)' : 'var(--text-muted)'
            }}
            data-testid={`tab-${tab.id}`}
          >
            <tab.icon size={16} />
            {tab.label}
            {tab.count > 0 && (
              <span 
                className="px-2 py-0.5 text-xs rounded-full"
                style={{ 
                  backgroundColor: activeTab === tab.id ? 'var(--accent-primary)' : 'var(--bg-sunken)',
                  color: activeTab === tab.id ? 'white' : 'var(--text-muted)'
                }}
              >
                {tab.count}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="rounded-xl p-6" style={{ backgroundColor: 'var(--bg-elevated)' }}>
        {/* Onglet Paramètres */}
        {activeTab === 'params' && (
          <div className="space-y-6">
            <h3 className="text-lg font-semibold flex items-center gap-2" style={{ color: 'var(--text-primary)' }}>
              <Settings className="text-blue-500" size={20} />
              Paramètres du Scénario
            </h3>
            
            {/* Stratégie de planification */}
            <div className="p-4 rounded-lg" style={{ backgroundColor: 'var(--bg-sunken)' }}>
              <div className="text-sm font-medium mb-3" style={{ color: 'var(--text-secondary)' }}>
                Stratégie de Planification
              </div>
              <div className="flex items-center gap-4">
                <div 
                  className="flex items-center gap-3 p-3 rounded-lg border-2"
                  style={{ 
                    backgroundColor: 'var(--bg-elevated)',
                    borderColor: schedulingStrategy === 'ASAP' ? '#3B82F6' : '#8B5CF6'
                  }}
                >
                  {schedulingStrategy === 'ASAP' ? (
                    <FastForward size={24} style={{ color: '#3B82F6' }} />
                  ) : (
                    <Rewind size={24} style={{ color: '#8B5CF6' }} />
                  )}
                  <div>
                    <div className="font-bold text-lg" style={{ color: 'var(--text-primary)' }}>
                      {schedulingStrategy === 'ASAP' ? 'Au plus tôt' : 'Au plus tard (JIT)'}
                    </div>
                    <div className="text-sm" style={{ color: 'var(--text-muted)' }}>
                      {schedulingStrategy === 'ASAP' 
                        ? 'Les opérations sont planifiées dès que possible'
                        : 'Les opérations sont planifiées le plus tard possible (Juste-à-temps)'
                      }
                    </div>
                  </div>
                </div>
              </div>
            </div>
            
            {/* Informations supplémentaires */}
            <div className="grid grid-cols-2 gap-4">
              <div className="p-4 rounded-lg" style={{ backgroundColor: 'var(--bg-sunken)' }}>
                <div className="text-xs font-medium uppercase mb-1" style={{ color: 'var(--text-muted)' }}>
                  Date de début planification
                </div>
                <div className="font-mono font-semibold" style={{ color: 'var(--text-primary)' }}>
                  {schedulingStart ? new Date(schedulingStart).toLocaleString('fr-FR') : '-'}
                </div>
              </div>
              <div className="p-4 rounded-lg" style={{ backgroundColor: 'var(--bg-sunken)' }}>
                <div className="text-xs font-medium uppercase mb-1" style={{ color: 'var(--text-muted)' }}>
                  Itérations matière
                </div>
                <div className="font-mono font-semibold" style={{ color: 'var(--text-primary)' }}>
                  {scheduleData.material_iteration || 1}
                </div>
              </div>
            </div>
            
            {/* Explication de la stratégie */}
            <div className="p-4 rounded-lg border" style={{ borderColor: 'var(--border-default)' }}>
              <div className="flex items-start gap-3">
                <Info size={20} style={{ color: 'var(--text-muted)', flexShrink: 0, marginTop: 2 }} />
                <div className="text-sm" style={{ color: 'var(--text-muted)' }}>
                  {schedulingStrategy === 'ASAP' ? (
                    <>
                      <strong>Mode Au plus tôt :</strong> Le moteur minimise le makespan (temps total de production). 
                      Les opérations démarrent dès que toutes les contraintes (machine, matière, calendrier) le permettent.
                      Ce mode maximise l'utilisation des ressources mais peut générer des encours importants.
                    </>
                  ) : (
                    <>
                      <strong>Mode Juste-à-temps :</strong> Le moteur repousse les opérations le plus tard possible 
                      tout en respectant les dates de besoin des ordres de fabrication.
                      Ce mode limite les encours et les entrées en stock anticipées.
                      Les opérations sans date de besoin sont planifiées en mode "au plus tôt".
                    </>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'priority' && (
          <div className="space-y-4">
            <h3 className="text-lg font-semibold flex items-center gap-2" style={{ color: 'var(--text-primary)' }}>
              <Zap className="text-yellow-500" size={20} />
              Propagation de Priorité
            </h3>
            
            {urgentOrders.length > 0 && (
              <div className="p-4 rounded-lg" style={{ backgroundColor: 'var(--bg-sunken)' }}>
                <div className="text-sm font-medium mb-2" style={{ color: 'var(--text-secondary)' }}>
                  OFs Urgents (priority=1)
                </div>
                <div className="flex flex-wrap gap-2">
                  {urgentOrders.map(of => (
                    <span 
                      key={of}
                      className="px-3 py-1 rounded-full text-sm font-medium"
                      style={{ backgroundColor: 'rgba(234, 179, 8, 0.2)', color: '#eab308' }}
                    >
                      {of}
                    </span>
                  ))}
                </div>
              </div>
            )}
            
            {priorityPropagation.length > 0 ? (
              <div className="space-y-3">
                <div className="text-sm" style={{ color: 'var(--text-muted)' }}>
                  Décisions de propagation automatique :
                </div>
                {priorityPropagation.map((prop, idx) => (
                  <div 
                    key={idx}
                    className="p-4 rounded-lg border-l-4"
                    style={{ 
                      backgroundColor: 'var(--bg-sunken)',
                      borderColor: '#eab308'
                    }}
                  >
                    <div className="flex items-center gap-3 mb-2">
                      <span className="px-2 py-1 rounded text-xs font-bold" style={{ backgroundColor: 'rgba(234, 179, 8, 0.2)', color: '#eab308' }}>
                        {prop.source_order}
                      </span>
                      <ArrowRight size={16} style={{ color: 'var(--text-muted)' }} />
                      <span className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                        consomme <strong>{prop.article_needed}</strong>
                      </span>
                      <ArrowRight size={16} style={{ color: 'var(--text-muted)' }} />
                      <span className="px-2 py-1 rounded text-xs font-bold" style={{ backgroundColor: 'rgba(234, 179, 8, 0.2)', color: '#eab308' }}>
                        {prop.target_order}
                      </span>
                    </div>
                    <div className="text-sm" style={{ color: 'var(--text-muted)' }}>
                      <Info size={14} className="inline mr-1" />
                      {prop.reason}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8" style={{ color: 'var(--text-muted)' }}>
                Aucune propagation de priorité dans ce scénario
              </div>
            )}
          </div>
        )}

        {activeTab === 'material' && (
          <div className="space-y-4">
            <h3 className="text-lg font-semibold flex items-center gap-2" style={{ color: 'var(--text-primary)' }}>
              <Clock className="text-blue-500" size={20} />
              Opérations Reportées pour Matière
            </h3>
            
            {materialDelayed.length > 0 ? (
              <div className="space-y-3">
                {materialDelayed.map((op, idx) => (
                  <div 
                    key={idx}
                    className="p-4 rounded-lg border-l-4"
                    style={{ 
                      backgroundColor: 'var(--bg-sunken)',
                      borderColor: '#3b82f6'
                    }}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-medium" style={{ color: 'var(--text-primary)' }}>
                        {op.operation_id}
                      </span>
                      <span className="text-sm px-2 py-1 rounded" style={{ backgroundColor: 'rgba(59, 130, 246, 0.2)', color: '#3b82f6' }}>
                        Reportée au {new Date(op.earliest_date).toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>
                    <div className="text-sm" style={{ color: 'var(--text-muted)' }}>
                      Composants bloquants : <strong>{op.blocking_components?.join(', ') || 'N/A'}</strong>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8" style={{ color: 'var(--text-muted)' }}>
                <CheckCircle size={32} className="mx-auto mb-2 text-green-500" />
                Aucune rupture matière dans ce scénario
              </div>
            )}
          </div>
        )}

        {activeTab === 'productions' && (
          <div className="space-y-4">
            <h3 className="text-lg font-semibold flex items-center gap-2" style={{ color: 'var(--text-primary)' }}>
              <Package className="text-green-500" size={20} />
              Entrées en Stock (Articles Fabriqués)
            </h3>
            
            {productions.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--border-default)' }}>
                      <th className="text-left py-3 px-4 text-sm font-medium" style={{ color: 'var(--text-muted)' }}>OF</th>
                      <th className="text-left py-3 px-4 text-sm font-medium" style={{ color: 'var(--text-muted)' }}>Article</th>
                      <th className="text-right py-3 px-4 text-sm font-medium" style={{ color: 'var(--text-muted)' }}>Quantité</th>
                      <th className="text-left py-3 px-4 text-sm font-medium" style={{ color: 'var(--text-muted)' }}>Entrée Stock</th>
                    </tr>
                  </thead>
                  <tbody>
                    {productions.map((prod, idx) => (
                      <tr 
                        key={idx}
                        style={{ borderBottom: '1px solid var(--border-default)' }}
                      >
                        <td className="py-3 px-4 font-medium" style={{ color: 'var(--text-primary)' }}>
                          {prod.order_id}
                        </td>
                        <td className="py-3 px-4">
                          <span className="px-2 py-1 rounded text-sm" style={{ backgroundColor: 'var(--bg-sunken)', color: 'var(--text-secondary)' }}>
                            {prod.article_id}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-right font-mono" style={{ color: 'var(--text-primary)' }}>
                          +{prod.quantity}
                        </td>
                        <td className="py-3 px-4 text-sm" style={{ color: 'var(--text-muted)' }}>
                          {new Date(prod.end_datetime).toLocaleDateString('fr-FR', { 
                            day: '2-digit', 
                            month: '2-digit',
                            hour: '2-digit',
                            minute: '2-digit'
                          })}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="text-center py-8" style={{ color: 'var(--text-muted)' }}>
                Aucune production enregistrée
              </div>
            )}
          </div>
        )}

        {activeTab === 'issues' && (
          <div className="space-y-4">
            <h3 className="text-lg font-semibold flex items-center gap-2" style={{ color: 'var(--text-primary)' }}>
              <AlertTriangle className="text-red-500" size={20} />
              Opérations Non Planifiées
            </h3>
            
            {unscheduledOps.length > 0 ? (
              <div className="space-y-3">
                {unscheduledOps.map((op, idx) => (
                  <div 
                    key={idx}
                    className="p-4 rounded-lg border-l-4"
                    style={{ 
                      backgroundColor: 'var(--bg-sunken)',
                      borderColor: '#ef4444'
                    }}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-medium" style={{ color: 'var(--text-primary)' }}>
                        {op.operation_id}
                      </span>
                      <span className="text-xs px-2 py-1 rounded" style={{ backgroundColor: 'rgba(239, 68, 68, 0.2)', color: '#ef4444' }}>
                        NON PLANIFIABLE
                      </span>
                    </div>
                    <div className="text-sm" style={{ color: 'var(--text-muted)' }}>
                      {op.reason}
                    </div>
                    {op.blocking_components?.length > 0 && (
                      <div className="text-sm mt-2" style={{ color: 'var(--text-muted)' }}>
                        Composants : {op.blocking_components.join(', ')}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8" style={{ color: 'var(--text-muted)' }}>
                <CheckCircle size={32} className="mx-auto mb-2 text-green-500" />
                Toutes les opérations ont été planifiées avec succès
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
