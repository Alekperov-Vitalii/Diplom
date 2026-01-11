'use client';

import { useEffect, useState } from 'react';
import { getCurrentState, CurrentState, healthCheck, getFanStatistics, FanStatistics, getSystemMode, SystemMode, getEnvironmentalState, EnvironmentalState } from '@/lib/api';
import Link from 'next/link';
import { Thermometer, Fan, AlertTriangle, Activity, Settings, Droplets, History, TrendingUp, Sliders } from 'lucide-react';
import FanCard from '@/components/FanCard';

export default function Dashboard() {
  const [state, setState] = useState<CurrentState | null>(null);
  const [fanStats, setFanStats] = useState<FanStatistics[]>([]);
  const [systemMode, setSystemMode] = useState<SystemMode | null>(null);
  const [envState, setEnvState] = useState<EnvironmentalState | null>(null);
  const [serverOnline, setServerOnline] = useState(true);
  const [loading, setLoading] = useState(true);

  // Polling каждые 5 секунд
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
    const interval = setInterval(fetchData, 5000);

    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-xl">Завантаження...</div>
      </div>
    );
  }

  if (!serverOnline) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <AlertTriangle className="w-16 h-16 text-red-500 mx-auto mb-4" />
          <h1 className="text-2xl font-bold mb-2">Сервер недоступний</h1>
          <p className="text-gray-800">Переконайтеся, що fog-сервер запущено на порту 8001</p>
        </div>
      </div>
    );
  }

  const criticalAlerts = state?.alerts.filter(a => a.severity === 'critical') || [];
  const warningAlerts = state?.alerts.filter(a => a.severity === 'warning') || [];

  return (
    <div className="min-h-screen bg-gray-50 text-gray-900 p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold mb-2">Дипломка - Версия 3.3 - 01.12.25</h1> {/* GPU Cooling System */ }
          <p className="text-gray-800">Дипломка моніторинг та керування охолодженням GPU-кластера </p>{/* Моніторинг та керування охолодженням GPU-кластера */ }
        </div>

        {/* Status Bar */}
        <div className="bg-white rounded-lg shadow p-4 mb-6 flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2">
              <Activity className="w-5 h-5 text-green-500" />
              <span className="font-medium">Система працює</span>
            </div>
            
            <div className="flex items-center space-x-2">
              {systemMode?.mode === 'auto' ? (
                <>
                  <span className="px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-sm font-medium">
                    🤖 Автоматичний режим
                  </span>
                </>
              ) : (
                <>
                  <span className="px-3 py-1 bg-purple-100 text-purple-700 rounded-full text-sm font-medium">
                    🎛️ Ручний режим
                  </span>
                </>
              )}
            </div>
          </div>
          
          <div className="text-sm text-gray-700">
            Оновлено: {state ? new Date(state.timestamp).toLocaleTimeString('uk-UA') : '—'}
          </div>
        </div>

        {/* Navigation Buttons */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <Link href="/history" className="flex items-center justify-center p-4 bg-white rounded-lg shadow border-2 border-transparent hover:border-blue-500 hover:shadow-md transition-all group">
            <div className="bg-blue-100 p-3 rounded-full mr-4 group-hover:bg-blue-200 transition-colors">
              <History className="w-6 h-6 text-blue-600" />
            </div>
            <div className="text-left">
              <div className="font-bold text-lg text-gray-900">Історія</div>
              <div className="text-sm text-gray-500">Графіки та статистика</div>
            </div>
          </Link>
          
          <Link href="/trends" className="flex items-center justify-center p-4 bg-white rounded-lg shadow border-2 border-transparent hover:border-purple-500 hover:shadow-md transition-all group">
            <div className="bg-purple-100 p-3 rounded-full mr-4 group-hover:bg-purple-200 transition-colors">
              <TrendingUp className="w-6 h-6 text-purple-600" />
            </div>
            <div className="text-left">
              <div className="font-bold text-lg text-gray-900">Тренди</div>
              <div className="text-sm text-gray-500">Аналіз ефективності</div>
            </div>
          </Link>
          
          <Link href="/control" className="flex items-center justify-center p-4 bg-white rounded-lg shadow border-2 border-transparent hover:border-green-500 hover:shadow-md transition-all group">
            <div className="bg-green-100 p-3 rounded-full mr-4 group-hover:bg-green-200 transition-colors">
              <Sliders className="w-6 h-6 text-green-600" />
            </div>
            <div className="text-left">
              <div className="font-bold text-lg text-gray-900">Керування</div>
              <div className="text-sm text-gray-500">Вентилятори та середовище</div>
            </div>
          </Link>
        </div>

        {/* Alerts */}
        {(criticalAlerts.length > 0 || warningAlerts.length > 0) && (
          <div className="mb-6 space-y-2">
            {criticalAlerts.map(alert => (
              <div key={alert.gpu_id} className="bg-red-100 border-l-4 border-red-500 p-4 rounded">
                <div className="flex items-center">
                  <AlertTriangle className="w-5 h-5 text-red-500 mr-2" />
                  <span className="font-bold text-red-700">
                    КРИТИЧНО: GPU {alert.gpu_id} — {alert.temperature.toFixed(1)}°C (поріг {alert.threshold}°C)
                  </span>
                </div>
              </div>
            ))}
            {warningAlerts.map(alert => (
              <div key={alert.gpu_id} className="bg-yellow-100 border-l-4 border-yellow-500 p-4 rounded">
                <div className="flex items-center">
                  <AlertTriangle className="w-5 h-5 text-yellow-500 mr-2" />
                  <span className="font-medium text-yellow-700">
                    Попередження: GPU {alert.gpu_id} — {alert.temperature.toFixed(1)}°C
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Environmental Status */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h2 className="text-2xl font-bold mb-4 flex items-center">
            <Droplets className="w-6 h-6 mr-2" />
            Параметри навколишнього середовища
          </h2>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Humidity Card */}
            <div className={`p-4 rounded-lg border-l-4 ${
              envState?.humidity && envState.humidity >= 40 && envState.humidity <= 60 
                ? 'border-green-500 bg-green-50' 
                : envState?.humidity && (envState.humidity < 30 || envState.humidity > 70)
                ? 'border-red-500 bg-red-50'
                : 'border-yellow-500 bg-yellow-50'
            }`}>
              <div className="text-sm text-gray-600 mb-1">Вологість</div>
              <div className="text-3xl font-bold">
                {envState?.humidity?.toFixed(1) ?? '--'}%
              </div>
              <div className="text-xs mt-2">
                {envState?.humidity && envState.humidity >= 40 && envState.humidity <= 60 
                  ? '✓ Оптимально' 
                  : envState?.humidity && envState.humidity < 40 
                  ? '⚠ Низька - ризик статики'
                  : '⚠ Висока - ризик корозії'}
              </div>
            </div>
            
            {/* Dust Card */}
            <div className={`p-4 rounded-lg border-l-4 ${
              envState?.dust && envState.dust < 25 
                ? 'border-green-500 bg-green-50' 
                : envState?.dust && envState.dust < 50
                ? 'border-yellow-500 bg-yellow-50'
                : 'border-red-500 bg-red-50'
            }`}>
              <div className="text-sm text-gray-600 mb-1">Рівень пилу</div>
              <div className="text-3xl font-bold">
                {envState?.dust?.toFixed(1) ?? '--'} μg/m³
              </div>
              <div className="text-xs mt-2">
                {envState?.dust && envState.dust < 25 
                  ? '✓ Низький' 
                  : envState?.dust && envState.dust < 50 
                  ? '⚠ Помірний'
                  : '🚨 Високий - потрібне очищення'}
              </div>
            </div>
            
            {/* Actuators Status */}
            <div className="p-4 rounded-lg border-l-4 border-blue-500 bg-blue-50">
              <div className="text-sm text-gray-600 mb-1">Активні засоби контролю</div>
              {envState?.actuators.dehumidifier_active && (
                <div className="text-sm mt-2">
                  🌬️ Осушувач: {envState.actuators.dehumidifier_power}%
                </div>
              )}
              {envState?.actuators.humidifier_active && (
                <div className="text-sm mt-2">
                  💧 Зволожувач: {envState.actuators.humidifier_power}%
                </div>
              )}
              {!envState?.actuators.dehumidifier_active && !envState?.actuators.humidifier_active && (
                <div className="text-sm mt-2 text-gray-500">— Немає активних засобів</div>
              )}
            </div>
          </div>
          
          {/* Environmental Alerts */}
          {envState?.alerts && envState.alerts.length > 0 && (
            <div className="mt-4 space-y-2">
              {envState.alerts.map((alert, idx) => (
                <div key={idx} className={`p-3 rounded-lg ${
                  alert.severity === 'critical' ? 'bg-red-100 text-red-800' : 'bg-yellow-100 text-yellow-800'
                }`}>
                  <div className="font-medium">{alert.message}</div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* GPU Cards */}
        <div className="mb-8">
          <h2 className="text-2xl font-bold mb-4">🎮 Температури GPU</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {state?.gpu_temps
              .sort((a, b) => a.gpu_id - b.gpu_id)
              .map(gpu => {
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
                  
                  <div className="text-3xl font-bold mb-4">
                    {temp.toFixed(1)}°C
                  </div>
                  
                  <div className="mb-4">
                    <div className="flex justify-between text-xs text-gray-600 mb-1">
                      <span>Навантаження GPU</span>
                      <span className="font-semibold">{gpu.load ? gpu.load.toFixed(0) : 0}%</span>
                    </div>
                    <div className="w-full bg-gray-100 rounded-full h-2">
                      <div 
                        className={`h-2 rounded-full transition-all duration-500 ${
                          (gpu.load || 0) > 90 ? 'bg-red-500' : 
                          (gpu.load || 0) > 50 ? 'bg-blue-500' : 'bg-green-500'
                        }`}
                        style={{ width: `${gpu.load || 0}%` }}
                      ></div>
                    </div>
                  </div>
                  
                  <div className="flex items-center text-sm text-gray-800">
                    <Fan className="w-4 h-4 mr-1" />
                    <span>{systemMode?.mode === 'auto' ? 'Автоматичне' : 'Ручне'} керування</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Fan Cards */}
        <div className="mb-8">
          <h2 className="text-2xl font-bold mb-4">🌀 Вентилятори</h2>
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
            📊 Історія та графіки
          </a>
          <a
            href="/control"
            className="px-6 py-3 bg-purple-500 text-white rounded-lg hover:bg-purple-600 transition flex items-center space-x-2"
          >
            <Settings className="w-5 h-5" />
            <span>🎛️ Ручне керування</span>
          </a>
</div>
</div>
</div>
);
}
