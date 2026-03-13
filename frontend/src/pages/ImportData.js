import { useState } from 'react';
import axios from 'axios';
import { Upload } from 'lucide-react';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const importTypes = [
  { key: 'manufacturing-orders', label: 'Ordres de Fabrication', testId: 'import-orders' },
  { key: 'operations', label: 'Opérations', testId: 'import-operations' },
  { key: 'articles', label: 'Articles', testId: 'import-articles' },
  { key: 'stocks', label: 'Stocks', testId: 'import-stocks' },
];

export default function ImportData() {
  const [uploading, setUploading] = useState({});

  const handleFileUpload = async (type, file) => {
    if (!file) return;

    setUploading((prev) => ({ ...prev, [type]: true }));

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await axios.post(`${API}/import/${type}`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      if (response.data.success) {
        toast.success(`Import réussi: ${response.data.records_imported} enregistrements`);
      } else {
        toast.error(`Erreur d'import: ${response.data.message}`);
      }
    } catch (error) {
      console.error('Upload error:', error);
      toast.error(`Erreur d'import: ${error.message}`);
    } finally {
      setUploading((prev) => ({ ...prev, [type]: false }));
    }
  };

  return (
    <div className="space-y-6">
      <div className="bg-white border border-slate-200 rounded-sm shadow-sm p-5">
        <h3 className="text-xl font-semibold text-slate-800 mb-2">Import de données ERP</h3>
        <p className="text-sm text-slate-600 leading-normal mb-6">
          Importez vos fichiers CSV depuis l'ERP Infor LN. Chaque fichier doit respecter le format attendu.
        </p>

        <div className="space-y-4">
          {importTypes.map((type) => (
            <div
              key={type.key}
              className="border border-slate-200 rounded-sm p-4 hover:border-slate-300 transition-colors"
            >
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium text-slate-900">{type.label}</p>
                  <p className="text-xs text-slate-500 mt-1">Format CSV requis</p>
                </div>
                <label
                  data-testid={type.testId}
                  className="cursor-pointer inline-flex items-center gap-2 bg-slate-900 text-white hover:bg-slate-800 rounded-sm px-4 py-2 text-sm font-medium transition-colors shadow-sm"
                >
                  <Upload size={16} />
                  {uploading[type.key] ? 'Import...' : 'Choisir fichier'}
                  <input
                    type="file"
                    accept=".csv"
                    className="hidden"
                    onChange={(e) => handleFileUpload(type.key, e.target.files[0])}
                    disabled={uploading[type.key]}
                  />
                </label>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="bg-white border border-slate-200 rounded-sm shadow-sm p-5">
        <h3 className="text-lg font-semibold text-slate-800 mb-3">Format des fichiers</h3>
        <div className="space-y-3 text-sm text-slate-600">
          <div>
            <p className="font-medium text-slate-900">Ordres de Fabrication:</p>
            <code className="text-xs font-mono bg-slate-50 px-2 py-1 rounded border border-slate-200">
              id, article, quantity, due_date, status
            </code>
          </div>
          <div>
            <p className="font-medium text-slate-900">Opérations:</p>
            <code className="text-xs font-mono bg-slate-50 px-2 py-1 rounded border border-slate-200">
              id, order_id, operation_number, sequence, production_time_minutes, setup_time_minutes
            </code>
          </div>
          <div>
            <p className="font-medium text-slate-900">Articles:</p>
            <code className="text-xs font-mono bg-slate-50 px-2 py-1 rounded border border-slate-200">
              id, description
            </code>
          </div>
          <div>
            <p className="font-medium text-slate-900">Stocks:</p>
            <code className="text-xs font-mono bg-slate-50 px-2 py-1 rounded border border-slate-200">
              article, quantity
            </code>
          </div>
        </div>
      </div>
    </div>
  );
}