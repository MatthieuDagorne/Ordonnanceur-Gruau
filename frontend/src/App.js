import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Toaster } from '@/components/ui/sonner';
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
import GanttView from '@/pages/GanttView';
import Scenarios from '@/pages/Scenarios';
import DiagnosticAssignment from '@/pages/DiagnosticAssignment';
import ProjectedStock from '@/pages/ProjectedStock';
import APSDashboard from '@/pages/APSDashboard';
import '@/App.css';

function App() {
  return (
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
            <Route path="aps" element={<APSDashboard />} />
            <Route path="gantt/:scenarioId" element={<GanttView />} />
            <Route path="scenarios" element={<Scenarios />} />
          </Route>
        </Routes>
      </BrowserRouter>
      <Toaster position="top-right" />
    </div>
  );
}

export default App;