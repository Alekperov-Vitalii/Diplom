'use client';

import { useEffect, useState, useRef } from 'react';
import Link from 'next/link';
import { ArrowLeft, AlertTriangle, Save, RotateCcw } from 'lucide-react';
import { 
  getSystemMode, 
  setSystemMode, 
  getCurrentState, 
  setManualFanControl,
  getUserActions,
  getEnvironmentalState,
  setEnvironmentalControl,
  SystemMode,
  CurrentState,
  UserAction,
  EnvironmentalState
} from '@/lib/api';

export default function Control() {
  const [mode, setMode] = useState<SystemMode | null>(null);
  const [state, setState] = useState<CurrentState | null>(null);
  const [actions, setActions] = useState<UserAction[]>([]);
  const [fanPWM, setFanPWM] = useState<{ [key: number]: number }>({});
  const [envState, setEnvState] = useState<EnvironmentalState | null>(null);
  const [dehumidifierActive, setDehumidifierActive] = useState(false);
  const [dehumidifierPower, setDehumidifierPower] = useState(75);
  const [humidifierActive, setHumidifierActive] = useState(false);
  const [humidifierPower, setHumidifierPower] = useState(75);

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const envInitialized = useRef(false);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [modeData, stateData, actionsData] = await Promise.all([
          getSystemMode(),
          getCurrentState(),
          getUserActions(10)
        ]);

        setMode(modeData);
        setState(stateData);
        setActions(actionsData);
        
        // Fetch environmental state
        const envData = await getEnvironmentalState();
        setEnvState(envData);
        if (!envInitialized.current) {
          setDehumidifierActive(envData.actuators.dehumidifier_active);
          setDehumidifierPower(envData.actuators.dehumidifier_power);
          setHumidifierActive(envData.actuators.humidifier_active);
          setHumidifierPower(envData.actuators.humidifier_power);
          envInitialized.current = true;
        }
        // fanPWM НЕ скидаємо!
      } catch (error) {
        console.error('Error fetching data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);

  // Ініціалізація PWM тільки при першому рендері
  useEffect(() => {
    if (Object.keys(fanPWM).length === 0) {
      const initialPWM: { [key: number]: number } = {};
      for (let i = 1; i <= 16; i++) {
        initialPWM[i] = 20;
      }
      setFanPWM(initialPWM);
    }
  }, [fanPWM]);

  const handleModeSwitch = async (newMode: 'auto' | 'manual') => {
    try {
      await setSystemMode(newMode);
      setMode({ ...mode!, mode: newMode });
      
      if (newMode === 'auto') {
        alert('✓ Систему переключено на автоматичний режим');
      }
    } catch (error) {
      alert('Помилка перемикання режиму: ' + error);
    }
  };

  const handleApplyManualControl = async () => {
    if (mode?.mode !== 'manual') {
      alert('Спочатку переключіться на ручний режим!');
      return;
    }

    // Перевірка: попередження про гарячі GPU
    const warnings = [];
    for (let i = 1; i <= 16; i++) {
      const gpuTemp = state?.gpu_temps.find(g => g.gpu_id === i)?.temperature || 0;
      const pwm = fanPWM[i];
      
      if (gpuTemp > 70 && pwm < 60) {
        warnings.push(`GPU ${i}: ${gpuTemp.toFixed(1)}°C, але PWM лише ${pwm}%`);
      }
    }

    if (warnings.length > 0) {
      const confirmed = confirm(
        '⚠️ ПОПЕРЕДЖЕННЯ:\n\n' +
        warnings.join('\n') +
        '\n\nГПУ можуть перегрітися. Продовжити?'
      );
      if (!confirmed) return;
    }

    setSaving(true);
    try {
      const commands = Object.keys(fanPWM).map(fanId => ({
        fan_id: parseInt(fanId),
        pwm_duty: fanPWM[parseInt(fanId)]
      }));

      await setManualFanControl(commands);
      alert('✓ Ручні команди застосовано успішно!');
      
      // Оновлюємо історію дій
      const newActions = await getUserActions(10);
      setActions(newActions);
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : String(error);
      alert('Помилка: ' + message);
    } finally {
      setSaving(false);
    }
  };

  const applyProfile = (profile: 'quiet' | 'balanced' | 'max') => {
    const profiles = {
      quiet: 25,
      balanced: 50,
      max: 100
    };
    
    const newPWM: { [key: number]: number } = {};
    for (let i = 1; i <= 16; i++) {
      newPWM[i] = profiles[profile];
    }
    setFanPWM(newPWM);
  };

  if (loading) return <div className="p-8">Завантаження...</div>;

  return (
    <div className="min-h-screen bg-gray-50 text-gray-900 p-8">
      <div className="max-w-6xl mx-auto">
        <Link href="/" className="flex items-center text-blue-500 hover:text-blue-600 mb-4 transition-colors">
          <ArrowLeft className="w-4 h-4 mr-1" />
          Назад до Dashboard
        </Link>
        
        <div className="flex flex-col md:flex-row md:items-center justify-between mb-8 gap-4">
          <h1 className="text-3xl font-bold text-gray-900">🎛️ Панель керування системою</h1>
          <div className="flex items-center bg-white px-4 py-2 rounded-full shadow-sm border border-gray-200">
            <div className={`h-3 w-3 rounded-full mr-2 ${mode?.mode === 'auto' ? 'bg-blue-500 animate-pulse' : 'bg-purple-500 animate-pulse'}`}></div>
            <span className="text-sm font-medium text-gray-600">
              Поточний режим: <strong className={mode?.mode === 'auto' ? 'text-blue-600' : 'text-purple-600'}>{mode?.mode === 'auto' ? 'АВТОМАТИЧНИЙ' : 'РУЧНИЙ'}</strong>
            </span>
          </div>
        </div>
        
        {/* Mode Switcher Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          <button
            onClick={() => handleModeSwitch('auto')}
            className={`relative p-6 rounded-xl border-2 text-left transition-all duration-300 hover:shadow-lg group ${
              mode?.mode === 'auto'
                ? 'bg-blue-50 border-blue-500 ring-2 ring-blue-200'
                : 'bg-white border-gray-200 hover:border-blue-300'
            }`}
          >
            <div className="absolute top-4 right-4 text-3xl opacity-50 group-hover:opacity-100 transition-opacity">🤖</div>
            <h3 className={`text-xl font-bold mb-2 ${mode?.mode === 'auto' ? 'text-blue-700' : 'text-gray-900'}`}>
              Автоматичний режим
            </h3>
            <p className="text-sm text-gray-600 leading-relaxed mb-4">
              Повністю автоматичне керування вентиляторами та мікрокліматом.
              Система самостійно реагує на зміни температури, вологості та запиленості.
            </p>
            {mode?.mode === 'auto' && (
              <div className="text-xs font-semibold text-blue-600 bg-blue-100 px-2 py-1 rounded inline-block">
                ✓ АКТИВНО
              </div>
            )}
          </button>
          
          <button
            onClick={() => handleModeSwitch('manual')}
            className={`relative p-6 rounded-xl border-2 text-left transition-all duration-300 hover:shadow-lg group ${
              mode?.mode === 'manual'
                ? 'bg-purple-50 border-purple-500 ring-2 ring-purple-200'
                : 'bg-white border-gray-200 hover:border-purple-300'
            }`}
          >
            <div className="absolute top-4 right-4 text-3xl opacity-50 group-hover:opacity-100 transition-opacity">🎛️</div>
            <h3 className={`text-xl font-bold mb-2 ${mode?.mode === 'manual' ? 'text-purple-700' : 'text-gray-900'}`}>
              Ручний режим
            </h3>
            <p className="text-sm text-gray-600 leading-relaxed mb-4">
              Повний контроль над кожним вентилятором та пристроями клімату.
              Використовуйте для тестування, спеціальних сценаріїв або екстреного втручання.
            </p>
            {mode?.mode === 'manual' && (
              <div className="text-xs font-semibold text-purple-600 bg-purple-100 px-2 py-1 rounded inline-block">
                ✓ АКТИВНО
              </div>
            )}
          </button>
        </div>

        {/* Info Message for Auto Mode */}
        {mode?.mode === 'auto' && (
          <div className="bg-blue-50 border-l-4 border-blue-500 p-4 rounded mb-8 animate-fade-in">
            <div className="flex">
              <div className="flex-shrink-0">⚠️</div>
              <div className="ml-3">
                <p className="text-sm text-blue-700 font-medium">
                  Елементи керування заблоковано в автоматичному режимі
                </p>
                <p className="text-sm text-blue-600 mt-1">
                  Щоб змінити швидкість вентиляторів або налаштування клімату, переключіться в ручний режим вище.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Manual Controls Container (Always visible but disabled in Auto) */}
        <div className={`transition-all duration-500 ${mode?.mode !== 'manual' ? 'opacity-50 pointer-events-none grayscale-[0.3] filter' : ''}`}>
             
            {/* Fan Profiles */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
              <h2 className="text-xl font-bold mb-4 text-gray-800 flex items-center">
                <span className="bg-gray-100 p-2 rounded-lg mr-3">🚀</span>
                Швидкі профілі
              </h2>
              
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <button
                  onClick={() => applyProfile('quiet')}
                  disabled={mode?.mode !== 'manual'}
                  className="p-4 border-2 border-gray-100 rounded-xl hover:border-green-500 hover:bg-green-50 transition-all flex flex-col items-center justify-center text-center group"
                >
                  <div className="text-3xl mb-2 group-hover:scale-110 transition-transform">🔇</div>
                  <div className="font-bold text-gray-900">Тихий режим</div>
                  <div className="text-sm text-gray-500">25% PWM</div>
                </button>
                
                <button
                  onClick={() => applyProfile('balanced')}
                  disabled={mode?.mode !== 'manual'}
                  className="p-4 border-2 border-gray-100 rounded-xl hover:border-blue-500 hover:bg-blue-50 transition-all flex flex-col items-center justify-center text-center group"
                >
                  <div className="text-3xl mb-2 group-hover:scale-110 transition-transform">⚖️</div>
                  <div className="font-bold text-gray-900">Збалансований</div>
                  <div className="text-sm text-gray-500">50% PWM</div>
                </button>
                
                <button
                  onClick={() => applyProfile('max')}
                  disabled={mode?.mode !== 'manual'}
                  className="p-4 border-2 border-gray-100 rounded-xl hover:border-red-500 hover:bg-red-50 transition-all flex flex-col items-center justify-center text-center group"
                >
                  <div className="text-3xl mb-2 group-hover:scale-110 transition-transform">🔥</div>
                  <div className="font-bold text-gray-900">Максимум</div>
                  <div className="text-sm text-gray-500">100% PWM</div>
                </button>
              </div>
            </div>

            {/* Fan Sliders */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
              <h2 className="text-xl font-bold mb-4 text-gray-800 flex items-center">
                <span className="bg-gray-100 p-2 rounded-lg mr-3">💨</span>
                Налаштування вентиляторів
              </h2>
              
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-2 gap-6">
                {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16].map(fanId => {
                  const gpuTemp = state?.gpu_temps.find(g => g.gpu_id === fanId)?.temperature || 0;
                  const pwm = fanPWM[fanId] || 20;
                  const rpm = Math.round(800 + (5000 - 800) * pwm / 100);
                  const isWarning = gpuTemp > 70 && pwm < 60;
                  
                  return (
                    <div key={fanId} className={`border rounded-lg p-4 transition-all ${isWarning ? 'bg-yellow-50 border-yellow-200' : 'hover:border-gray-300'}`}>
                      <div className="flex justify-between items-center mb-2">
                        <span className="font-bold text-gray-700">Вентилятор {fanId}</span>
                        <span className={`text-sm font-mono px-2 py-1 rounded ${gpuTemp > 70 ? 'bg-red-100 text-red-700' : 'bg-gray-100 text-gray-600'}`}>
                          GPU: {gpuTemp.toFixed(1)}°C
                        </span>
                      </div>
                      
                      {isWarning && (
                        <div className="text-yellow-700 text-xs font-semibold mb-2 flex items-center">
                          ⚠️ Ризик перегріву! Рекомендовано &gt;60%
                        </div>
                      )}
                      
                      <div className="flex items-center space-x-4">
                        <input
                          type="range"
                          min="0"
                          max="100"
                          value={pwm}
                          disabled={mode?.mode !== 'manual'}
                          onChange={(e) => setFanPWM({ ...fanPWM, [fanId]: parseInt(e.target.value) })}
                          className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
                        />
                        <span className="font-bold w-12 text-right">{pwm}%</span>
                      </div>
                      
                      <div className="text-xs text-gray-500 mt-1 text-right">
                        ~{rpm} RPM
                      </div>
                    </div>
                  );
                })}
              </div>
              
              <div className="mt-8 flex flex-col md:flex-row space-y-4 md:space-y-0 md:space-x-4 items-center">
                <button
                  onClick={handleApplyManualControl}
                  disabled={saving || mode?.mode !== 'manual'}
                  className="w-full md:w-auto flex-1 bg-gradient-to-r from-purple-500 to-indigo-600 hover:from-purple-600 hover:to-indigo-700 text-white font-bold py-3 px-8 rounded-xl shadow-lg transform active:scale-95 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center space-x-2"
                >
                  <Save className="w-5 h-5" />
                  <span>{saving ? 'Застосування...' : 'Застосувати зміни вентиляторів'}</span>
                </button>
                
                <button
                  onClick={() => applyProfile('balanced')}
                  disabled={mode?.mode !== 'manual'}
                  className="w-full md:w-auto bg-gray-100 text-gray-700 font-medium py-3 px-6 rounded-xl hover:bg-gray-200 transition flex items-center justify-center space-x-2 disabled:opacity-50"
                >
                  <RotateCcw className="w-4 h-4" />
                  <span>Скинути</span>
                </button>
              </div>
            </div>

            {/* Environmental Controls */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
              <h2 className="text-xl font-bold mb-6 text-gray-800 flex items-center">
                <span className="bg-gray-100 p-2 rounded-lg mr-3">🌡️</span>
                Керування навколишнім середовищем
              </h2>
              
              {/* Current State Display */}
              <div className="bg-indigo-50 p-4 rounded-xl mb-6 border border-indigo-100">
                <h3 className="text-xs font-semibold text-indigo-500 uppercase tracking-wider mb-2">Поточні показники</h3>
                <div className="grid grid-cols-2 gap-4">
                  <div className="flex items-end">
                    <span className="text-2xl font-bold text-gray-900">{envState?.humidity?.toFixed(1) ?? '--'}</span>
                    <span className="text-sm text-gray-500 ml-1 mb-1">% вологості</span>
                  </div>
                  <div className="flex items-end">
                    <span className="text-2xl font-bold text-gray-900">{envState?.dust?.toFixed(1) ?? '--'}</span>
                    <span className="text-sm text-gray-500 ml-1 mb-1">μg/m³ пилу</span>
                  </div>
                </div>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                {/* Dehumidifier */}
                <div className="bg-gray-50 rounded-xl p-5 border border-gray-200">
                  <div className="flex items-center justify-between mb-4">
                    <label className="text-lg font-bold text-gray-800">Осушувач повітря</label>
                    <button
                      onClick={() => setDehumidifierActive(!dehumidifierActive)}
                      disabled={mode?.mode !== 'manual'}
                      className={`px-4 py-1.5 rounded-full text-sm font-bold transition-colors ${
                        dehumidifierActive 
                          ? 'bg-blue-600 text-white shadow-md' 
                          : 'bg-gray-200 text-gray-500'
                      }`}
                    >
                      {dehumidifierActive ? 'ON' : 'OFF'}
                    </button>
                  </div>
                  
                  <div className="mb-2 flex justify-between text-sm font-medium text-gray-600">
                    <span>Потужність</span>
                    <span>{dehumidifierPower}%</span>
                  </div>
                  
                  <input
                    type="range"
                    min="0"
                    max="100"
                    value={dehumidifierPower}
                    onChange={(e) => setDehumidifierPower(parseInt(e.target.value))}
                    disabled={!dehumidifierActive || mode?.mode !== 'manual'}
                    className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600 mb-4"
                  />
                  
                  <div className="text-xs text-blue-700 bg-blue-100 p-3 rounded-lg flex items-start">
                    <span className="mr-2">ℹ️</span>
                    Прогноз: -{(dehumidifierPower * 0.05).toFixed(1)}% вологості / год
                  </div>
                </div>
                
                {/* Humidifier */}
                <div className="bg-gray-50 rounded-xl p-5 border border-gray-200">
                  <div className="flex items-center justify-between mb-4">
                    <label className="text-lg font-bold text-gray-800">Зволожувач повітря</label>
                    <button
                      onClick={() => setHumidifierActive(!humidifierActive)}
                      disabled={mode?.mode !== 'manual'}
                      className={`px-4 py-1.5 rounded-full text-sm font-bold transition-colors ${
                        humidifierActive 
                          ? 'bg-blue-600 text-white shadow-md' 
                          : 'bg-gray-200 text-gray-500'
                      }`}
                    >
                      {humidifierActive ? 'ON' : 'OFF'}
                    </button>
                  </div>
                  
                  <div className="mb-2 flex justify-between text-sm font-medium text-gray-600">
                    <span>Потужність</span>
                    <span>{humidifierPower}%</span>
                  </div>
                  
                  <input
                    type="range"
                    min="0"
                    max="100"
                    value={humidifierPower}
                    onChange={(e) => setHumidifierPower(parseInt(e.target.value))}
                    disabled={!humidifierActive || mode?.mode !== 'manual'}
                    className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600 mb-4"
                  />
                  
                  <div className="text-xs text-blue-700 bg-blue-100 p-3 rounded-lg flex items-start">
                    <span className="mr-2">ℹ️</span>
                    Прогноз: +{(humidifierPower * 0.05).toFixed(1)}% вологості / год
                  </div>
                </div>
              </div>
              
              <div className="mt-8">
                <button
                  onClick={async () => {
                    try {
                      await setEnvironmentalControl({
                        dehumidifier_active: dehumidifierActive,
                        dehumidifier_power: dehumidifierPower,
                        humidifier_active: humidifierActive,
                        humidifier_power: humidifierPower
                      });
                      alert('✓ Налаштування навколишнього середовища застосовано!');
                    } catch (error) {
                      alert('Помилка: ' + error);
                    }
                  }}
                  disabled={mode?.mode !== 'manual'}
                  className="w-full bg-gradient-to-r from-green-500 to-teal-600 hover:from-green-600 hover:to-teal-700 text-white font-bold py-3 px-8 rounded-xl shadow-lg transform active:scale-95 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Застосувати налаштування середовища
                </button>
              </div>
            </div>
        </div>

        {/* Action History */}
        {actions.length > 0 && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <h2 className="text-xl font-bold mb-4 text-gray-800">📜 Історія дій користувача</h2>
            
            <div className="space-y-3">
              {actions.map((action, idx) => (
                <div key={idx} className="flex items-start space-x-3 text-sm border-b border-gray-100 pb-3 last:border-0 last:pb-0">
                  <span className="text-gray-500 font-mono whitespace-nowrap">
                    {new Date(action.timestamp).toLocaleTimeString('uk-UA')}
                  </span>
                  <span className="font-bold text-gray-700 bg-gray-100 px-2 py-0.5 rounded text-xs uppercase tracking-wide">
                    {action.action}
                  </span>
                  <span className="text-gray-600 flex-1 break-all font-mono text-xs mt-0.5">
                    {JSON.stringify(action.details)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}