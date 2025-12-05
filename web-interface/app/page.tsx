'use client';

import { useEffect, useState } from 'react';
import { getCurrentState, CurrentState, healthCheck, getFanStatistics, FanStatistics, getSystemMode, SystemMode } from '@/lib/api';
import { Thermometer, Fan, AlertTriangle, Activity, Settings } from 'lucide-react';
import FanCard from '@/components/FanCard';

export default function Dashboard() {
  const [state, setState] = useState<CurrentState | null>(null);
  const [fanStats, setFanStats] = useState<FanStatistics[]>([]);
  const [systemMode, setSystemMode] = useState<SystemMode | null>(null);
  const [serverOnline, setServerOnline] = useState(true);
  const [loading, setLoading] = useState(true);

  // Polling каждые 5 секунд
  useEffect(() => {
    const fetchData = async () => {
      try {
        const online = await healthCheck();
        setServerOnline(online);
        
        if (online) {
          const [data, stats, mode] = await Promise.all([
            getCurrentState(),
            getFanStatistics(),
            getSystemMode()
          ]);
          setState(data);
          setFanStats(stats);
          setSystemMode(mode);
        }
      } catch (error) {
        console.error('Error fetching data:', error);
        setServerOnline(false);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 5000);

    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-xl">Загрузка...</div>
      </div>
    );
  }

  if (!serverOnline) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <AlertTriangle className="w-16 h-16 text-red-500 mx-auto mb-4" />
          <h1 className="text-2xl font-bold mb-2">Сервер недоступен</h1>
          <p className="text-gray-600">Убедитесь что fog-сервер запущен на порту 8000</p>
        </div>
      </div>
    );
  }

  const criticalAlerts = state?.alerts.filter(a => a.severity === 'critical') || [];
  const warningAlerts = state?.alerts.filter(a => a.severity === 'warning') || [];

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold mb-2">GPU Cooling System</h1>
          <p className="text-gray-600">Мониторинг и управление охлаждением GPU-кластера</p>
        </div>

        {/* Status Bar */}
        <div className="bg-white rounded-lg shadow p-4 mb-6 flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2">
              <Activity className="w-5 h-5 text-green-500" />
              <span className="font-medium">Система работает</span>
            </div>
            
            <div className="flex items-center space-x-2">
              {systemMode?.mode === 'auto' ? (
                <>
                  <span className="px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-sm font-medium">
                    🤖 Автоматический режим
                  </span>
                </>
              ) : (
                <>
                  <span className="px-3 py-1 bg-purple-100 text-purple-700 rounded-full text-sm font-medium">
                    🎛️ Ручной режим
                  </span>
                </>
              )}
            </div>
          </div>
          
          <div className="text-sm text-gray-500">
            Обновлено: {state ? new Date(state.timestamp).toLocaleTimeString('ru-RU') : '—'}
          </div>
        </div>

        {/* Alerts */}
        {(criticalAlerts.length > 0 || warningAlerts.length > 0) && (
          <div className="mb-6 space-y-2">
            {criticalAlerts.map(alert => (
              <div key={alert.gpu_id} className="bg-red-100 border-l-4 border-red-500 p-4 rounded">
                <div className="flex items-center">
                  <AlertTriangle className="w-5 h-5 text-red-500 mr-2" />
                  <span className="font-bold text-red-700">
                    КРИТИЧНО: GPU {alert.gpu_id} — {alert.temperature.toFixed(1)}°C (порог {alert.threshold}°C)
                  </span>
                </div>
              </div>
            ))}
            {warningAlerts.map(alert => (
              <div key={alert.gpu_id} className="bg-yellow-100 border-l-4 border-yellow-500 p-4 rounded">
                <div className="flex items-center">
                  <AlertTriangle className="w-5 h-5 text-yellow-500 mr-2" />
                  <span className="font-medium text-yellow-700">
                    Предупреждение: GPU {alert.gpu_id} — {alert.temperature.toFixed(1)}°C
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* GPU Cards */}
        <div className="mb-8">
          <h2 className="text-2xl font-bold mb-4">🎮 GPU Температуры</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {state?.gpu_temps.map(gpu => {
              const temp = gpu.temperature;
              const isHot = temp >= 90;
              const isWarm = temp >= 70;
              
              return (
                <div
                  key={gpu.gpu_id}
                  className={`bg-white rounded-lg shadow p-6 border-l-4 ${
                    isHot ? 'border-red-500' : isWarm ? 'border-yellow-500' : 'border-green-500'
                  }`}
                >
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-bold">GPU {gpu.gpu_id}</h3>
                    <Thermometer className={`w-6 h-6 ${isHot ? 'text-red-500' : isWarm ? 'text-yellow-500' : 'text-green-500'}`} />
                  </div>
                  
                  <div className="text-3xl font-bold mb-1">
                    {temp.toFixed(1)}°C
                  </div>
                  
                  <div className="flex items-center text-sm text-gray-600">
                    <Fan className="w-4 h-4 mr-1" />
                    <span>{systemMode?.mode === 'auto' ? 'Автоматическое' : 'Ручное'} управление</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Fan Cards */}
        <div className="mb-8">
          <h2 className="text-2xl font-bold mb-4">🌀 Вентиляторы</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {fanStats.map(stats => {
              const gpuTemp = state?.gpu_temps.find(g => g.gpu_id === stats.fan_id)?.temperature || 0;
              return (
                <FanCard
                  key={stats.fan_id}
                  stats={stats}
                  gpuTemp={gpuTemp}
                  mode={systemMode?.mode || 'auto'}
                />
              );
            })}
          </div>
        </div>

        {/* Navigation */}
        <div className="flex space-x-4">
          <a
            href="/history"
            className="px-6 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition"
          >
            📊 История и графики
          </a>
          <a
            href="/control"
            className="px-6 py-3 bg-purple-500 text-white rounded-lg hover:bg-purple-600 transition flex items-center space-x-2"
          >
            <Settings className="w-5 h-5" />
            <span>🎛️ Ручное управление</span>
          </a>
</div>
</div>
</div>
);
}
