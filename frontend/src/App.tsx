import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider, useAuth } from './hooks/useAuth';
import { ProtectedRoute } from './components/ProtectedRoute';
import { Navbar } from './components/Navbar';
import { Sidebar } from './components/Sidebar';
import { useLiveFeed } from './hooks/useLiveFeed';
import { LoginPage } from './pages/LoginPage';
import { DashboardPage } from './pages/DashboardPage';
import { IncidentsPage } from './pages/IncidentsPage';
import { IncidentDetailPage } from './pages/IncidentDetailPage';
import { HospitalsPage } from './pages/HospitalsPage';
import { AmbulancesPage } from './pages/AmbulancesPage';
import { AmbulanceView } from './pages/AmbulanceView';
import { VehicleCheckInPage } from './pages/VehicleCheckInPage';
import { DevicesPage } from './pages/DevicesPage';
import { TrackingPage } from './pages/TrackingPage';
import { LiveMapPage } from './pages/LiveMapPage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

const MainLayout: React.FC = () => {
  const { token } = useAuth();
  const { isConnected } = useLiveFeed(token);

  return (
    <div className="min-h-screen flex flex-col bg-slate-950 text-slate-100">
      <Navbar isConnected={isConnected} />
      <div className="flex flex-1">
        <Sidebar />
        <main className="flex-1 p-6 overflow-y-auto max-w-[1600px] w-full mx-auto">
          <Routes>
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/map" element={<LiveMapPage />} />
            <Route path="/incidents" element={<IncidentsPage />} />
            <Route path="/incidents/:id" element={<IncidentDetailPage />} />
            <Route path="/hospitals" element={<HospitalsPage />} />
            <Route path="/ambulances" element={<AmbulancesPage />} />
            <Route path="/devices" element={<DevicesPage />} />
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </main>
      </div>
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/vehicle/:deviceCode" element={<VehicleCheckInPage />} />
            <Route path="/track/:token" element={<TrackingPage />} />
            <Route element={<ProtectedRoute />}>
              <Route path="/ambulance/:ambulanceCode" element={<AmbulanceView />} />
              <Route path="/*" element={<MainLayout />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
};


export default App;
