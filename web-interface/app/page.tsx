'use client';

import { useEffect, useState } from 'react';
import { getCurrentState, CurrentState, healthCheck, getFanStatistics, FanStatistics, getSystemMode, SystemMode, getEnvironmentalState, EnvironmentalState } from '@/lib/api';
import { StatusHero } from '@/components/dashboard/StatusHero';
import { NavGrid } from '@/components/dashboard/NavGrid';
import { ClimateWidget } from '@/components/dashboard/ClimateWidget';
import { AlertsSystem } from '@/components/dashboard/AlertsSystem';
import { GpuGrid } from '@/components/dashboard/GpuGrid';
import { FanGrid } from '@/components/dashboard/FanGrid';
import { AlertTriangle, Loader2 } from 'lucide-react';

export default function Dashboard() {
  const [state, setState] = useState<CurrentState | null>(null);
  const [fanStats, setFanStats] = useState<FanStatistics[]>([]);
  const [systemMode, setSystemMode] = useState<SystemMode | null>(null);
  const [envState, setEnvState] = useState<EnvironmentalState | null>(null);
  const [serverOnline, setServerOnline] = useState(true);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const online = await healthCheck();
        setServerOnline(online);
        
        if (online) {
          const [data, stats, mode, envData] = await Promise.all([
            getCurrentState(),
            getFanStatistics(),
            getSystemMode(),
            getEnvironmentalState()
          ]);
          setState(data);
          setFanStats(stats);
          setSystemMode(mode);
          setEnvState(envData);
        }
      } catch (error) {
        console.error('Error fetching data:', error);
        setServerOnline(false);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 2000); // Polling faster for smooth UI

    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-50">
        <div className="flex flex-col items-center gap-4">
           <Loader2 className="w-12 h-12 text-blue-500 animate-spin" />
           <div className="text-xl font-medium text-gray-500">Завантаження системи...</div>
        </div>
      </div>
    );
  }

  // If server offline, show full screen error
  if (!serverOnline) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-red-50 text-red-900 p-8">
        <div className="max-w-md w-full bg-white p-8 rounded-2xl shadow-xl text-center border-l-4 border-red-500">
          <div className="bg-red-100 w-20 h-20 rounded-full flex items-center justify-center mx-auto mb-6">
             <AlertTriangle className="w-10 h-10 text-red-600" />
          </div>
          <h1 className="text-3xl font-bold mb-3">З&apos;єднання втрачено</h1>
          <p className="text-gray-600 mb-6 text-lg">
            Fog-сервер не відповідає. Перевірте статус служби та підключення до бази даних.
          </p>
          <div className="bg-gray-100 p-4 rounded-lg font-mono text-sm text-gray-500">
             Host: localhost:8000
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50/50 text-gray-900 p-6 md:p-8 font-sans selection:bg-blue-100">
      <div className="max-w-7xl mx-auto">
        
        {/* Header Section */}
        <StatusHero 
           serverOnline={serverOnline} 
           systemMode={systemMode} 
           lastUpdated={state ? new Date(state.timestamp) : null} 
        />

        {/* Navigation */}
        <NavGrid />

        {/* Environmental Control Widget */}
        <ClimateWidget envState={envState} />

        {/* Main Monitoring Grids */}
        <GpuGrid gpuTemps={state?.gpu_temps || []} />
        
        <FanGrid fanStats={fanStats} systemMode={systemMode} />

        {/* Alerts Overlay */}
        <AlertsSystem alerts={state?.alerts || []} />
        
      </div>
    </div>
  );
}
