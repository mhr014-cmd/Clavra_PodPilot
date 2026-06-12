import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
import ProtectedRoute from "./routes/ProtectedRoute";

import LoginPage          from "./pages/LoginPage";
import DashboardPage      from "./pages/DashboardPage";
import ProductionPage     from "./pages/ProductionPage";
import ProductionLinePage from "./pages/ProductionLinePage";
import ShipmentPage       from "./pages/ShipmentPage";
import InventoryPage      from "./pages/InventoryPage";
import AICopilotPage      from "./pages/AICopilotPage";
import KnowledgePage      from "./pages/KnowledgePage";
import QualityPage        from "./pages/QualityPage";
import UnauthorizedPage   from "./pages/UnauthorizedPage";

export default function App() {
  return (
    <Router>
      <Routes>
        {/* Public */}
        <Route path="/login"        element={<LoginPage />} />
        <Route path="/unauthorized" element={<UnauthorizedPage />} />
        <Route path="/"             element={<Navigate to="/dashboard" replace />} />

        {/* All authenticated users */}
        <Route path="/dashboard" element={
          <ProtectedRoute><DashboardPage /></ProtectedRoute>
        }/>
        <Route path="/production" element={
          <ProtectedRoute><ProductionPage /></ProtectedRoute>
        }/>
        <Route path="/production-lines" element={
          <ProtectedRoute><ProductionLinePage /></ProtectedRoute>
        }/>
        <Route path="/shipments" element={
          <ProtectedRoute><ShipmentPage /></ProtectedRoute>
        }/>
        <Route path="/inventory" element={
          <ProtectedRoute><InventoryPage /></ProtectedRoute>
        }/>
        <Route path="/quality" element={
          <ProtectedRoute><QualityPage /></ProtectedRoute>
        }/>

        {/* Supervisor and above */}
        <Route path="/ai-copilot" element={
          <ProtectedRoute minRole="supervisor"><AICopilotPage /></ProtectedRoute>
        }/>
        <Route path="/knowledge" element={
          <ProtectedRoute minRole="supervisor"><KnowledgePage /></ProtectedRoute>
        }/>

        {/* Catch-all */}
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </Router>
  );
}
