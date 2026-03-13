import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Toaster } from '@/components/ui/sonner';
import Layout from '@/components/Layout';
import Dashboard from '@/pages/Dashboard';
import ImportData from '@/pages/ImportData';
import WorkCenters from '@/pages/WorkCenters';
import Machines from '@/pages/Machines';
import Calendars from '@/pages/Calendars';
import Unavailability from '@/pages/Unavailability';
import BusinessRules from '@/pages/BusinessRules';
import ManufacturingOrders from '@/pages/ManufacturingOrders';
import Scheduling from '@/pages/Scheduling';
import GanttView from '@/pages/GanttView';
import Scenarios from '@/pages/Scenarios';
import '@/App.css';

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Dashboard />} />
            <Route path="import" element={<ImportData />} />
            <Route path="work-centers" element={<WorkCenters />} />
            <Route path="machines" element={<Machines />} />
            <Route path="calendars" element={<Calendars />} />
            <Route path="unavailability" element={<Unavailability />} />
            <Route path="rules" element={<BusinessRules />} />
            <Route path="orders" element={<ManufacturingOrders />} />
            <Route path="scheduling" element={<Scheduling />} />
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