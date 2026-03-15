import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Toaster } from '@/components/ui/sonner';
import { ThemeProvider } from '@/contexts/ThemeContext';
import Layout from '@/components/Layout';
import Dashboard from '@/pages/Dashboard';
import ImportData from '@/pages/ImportData';
import CentresDeCharge from '@/pages/CentresDeCharge';
import Machines from '@/pages/Machines';
import Calendars from '@/pages/Calendars';
import Unavailability from '@/pages/Unavailability';
import BusinessRules from '@/pages/BusinessRules';
import ManufacturingOrders from '@/pages/ManufacturingOrders';
import Scheduling from '@/pages/Scheduling';
import GanttInteractive from '@/pages/GanttInteractive';
import ScenariosComparison from '@/pages/ScenariosComparison';
import DiagnosticAssignment from '@/pages/DiagnosticAssignment';
import ProjectedStock from '@/pages/ProjectedStock';
import ProjectedStockScenario from '@/pages/ProjectedStockScenario';
import APSDashboard from '@/pages/APSDashboard';
import MatrixView from '@/pages/MatrixView';
import '@/App.css';

function App() {
  return (
    <ThemeProvider>
      <div className="App">
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<Layout />}>
              <Route index element={<Dashboard />} />
              <Route path="import" element={<ImportData />} />
              <Route path="centres-de-charge" element={<CentresDeCharge />} />
              <Route path="machines" element={<Machines />} />
              <Route path="calendars" element={<Calendars />} />
              <Route path="unavailability" element={<Unavailability />} />
              <Route path="rules" element={<BusinessRules />} />
              <Route path="orders" element={<ManufacturingOrders />} />
              <Route path="scheduling" element={<Scheduling />} />
              <Route path="diagnostic" element={<DiagnosticAssignment />} />
              <Route path="projected-stock" element={<ProjectedStock />} />
              <Route path="projected-stock/:scenarioId" element={<ProjectedStockScenario />} />
              <Route path="aps" element={<APSDashboard />} />
              <Route path="matrix" element={<MatrixView />} />
              <Route path="gantt/:scenarioId" element={<GanttInteractive />} />
              <Route path="scenarios" element={<ScenariosComparison />} />
            </Route>
          </Routes>
        </BrowserRouter>
        <Toaster position="top-right" />
      </div>
    </ThemeProvider>
  );
}

export default App;