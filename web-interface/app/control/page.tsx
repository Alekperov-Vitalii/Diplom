'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { ArrowLeft, AlertTriangle, Save, RotateCcw } from 'lucide-react';
import { 
  getSystemMode, 
  setSystemMode, 
  getCurrentState, 
  setManualFanControl,
  getUserActions,
  SystemMode,
  CurrentState,
  UserAction
} from '@/lib/api';

export default function Control() {
  const [mode, setMode] = useState<SystemMode | null>(null);
  const [state, setState] = useState<CurrentState | null>(null);
  const [actions, setActions] = useState<UserAction[]>([]);
  const [fanPWM, setFanPWM] = useState<{ [key: number]: number }>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

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
        <Link href="/" className="flex items-center text-blue-500 hover:text-blue-600 mb-4">
          <ArrowLeft className="w-4 h-4 mr-1" />
          Назад до Dashboard
        </Link>
        
        <h1 className="text-3xl font-bold mb-6">🎛️ Ручне керування вентиляторами</h1>
        
        {/* Перемикач режиму */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h2 className="text-xl font-bold mb-4">Режим роботи системи</h2>
          
          <div className="flex space-x-4 mb-4">
            <button
              onClick={() => handleModeSwitch('auto')}
              className={`flex-1 py-3 px-6 rounded-lg font-medium transition ${
                mode?.mode === 'auto'
                  ? 'bg-blue-500 text-white'
                  : 'bg-gray-200 hover:bg-gray-300'
              }`}
            >
              🤖 Автоматичний (рекомендовано)
            </button>
            
            <button
              onClick={() => handleModeSwitch('manual')}
              className={`flex-1 py-3 px-6 rounded-lg font-medium transition ${
                mode?.mode === 'manual'
                  ? 'bg-purple-500 text-white'
                  : 'bg-gray-200 hover:bg-gray-300'
              }`}
            >
              🎛️ Ручний
            </button>
          </div>
          
          {mode?.mode === 'auto' && (
            <div className="bg-blue-50 border-l-4 border-blue-500 p-4 rounded">
              <p className="text-sm text-blue-700">
                ✓ Система працює в автоматичному режимі. Каскадний алгоритм керує вентиляторами на основі температури GPU та приміщення.
              </p>
            </div>
          )}
          
          {mode?.mode === 'manual' && (
            <div className="bg-yellow-50 border-l-4 border-yellow-500 p-4 rounded">
              <div className="flex items-start">
                <AlertTriangle className="w-5 h-5 text-yellow-600 mr-2 flex-shrink-0 mt-0.5" />
                <div className="text-sm text-yellow-700">
                  <p className="font-medium mb-1">Ручний режим активний</p>
                  <p>Ви повністю контролюєте вентилятори. Слідкуйте за температурами GPU, щоб уникнути перегріву.</p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Ручне керування */}
        {mode?.mode === 'manual' && (
          <>
            {/* Профілі */}
            <div className="bg-white rounded-lg shadow p-6 mb-6">
              <h2 className="text-xl font-bold mb-4">Попередньо встановлені профілі</h2>
              
              <div className="grid grid-cols-3 gap-4">
                <button
                  onClick={() => applyProfile('quiet')}
                  className="p-4 border-2 border-gray-300 rounded-lg hover:border-green-500 transition"
                >
                  <div className="text-2xl mb-2">🔇</div>
                  <div className="font-medium">Тихий режим</div>
                  <div className="text-sm text-gray-800">25% PWM</div>
                </button>
                
                <button
                  onClick={() => applyProfile('balanced')}
                  className="p-4 border-2 border-gray-300 rounded-lg hover:border-blue-500 transition"
                >
                  <div className="text-2xl mb-2">⚖️</div>
                  <div className="font-medium">Збалансований</div>
                  <div className="text-sm text-gray-800">50% PWM</div>
                </button>
                
                <button
                  onClick={() => applyProfile('max')}
                  className="p-4 border-2 border-gray-300 rounded-lg hover:border-red-500 transition"
                >
                  <div className="text-2xl mb-2">🔥</div>
                  <div className="font-medium">Максимум</div>
                  <div className="text-sm text-gray-800">100% PWM</div>
                </button>
              </div>
            </div>

            {/* Слайдери */}
            <div className="bg-white rounded-lg shadow p-6 mb-6">
              <h2 className="text-xl font-bold mb-4">Налаштування вентиляторів</h2>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16].map(fanId => {
                  const gpuTemp = state?.gpu_temps.find(g => g.gpu_id === fanId)?.temperature || 0;
                  const pwm = fanPWM[fanId] || 20;
                  const rpm = Math.round(800 + (5000 - 800) * pwm / 100);
                  const isWarning = gpuTemp > 70 && pwm < 60;
                  
                  return (
                    <div key={fanId} className="border rounded-lg p-4">
                      <div className="flex justify-between items-center mb-2">
                        <span className="font-medium">Вентилятор {fanId}</span>
                        <span className="text-sm text-gray-800">
                          GPU: {gpuTemp.toFixed(1)}°C
                        </span>
                      </div>
                      
                      {isWarning && (
                        <div className="bg-yellow-50 text-yellow-700 text-xs p-2 rounded mb-2">
                          ⚠️ GPU гарячий, рекомендовано &gt;60% PWM
                        </div>
                      )}
                      
                      <input
                        type="range"
                        min="0"
                        max="100"
                        value={pwm}
                        onChange={(e) => setFanPWM({ ...fanPWM, [fanId]: parseInt(e.target.value) })}
                        className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                      />
                      
                      <div className="flex justify-between text-sm mt-2">
                        <span className="text-gray-800">PWM: {pwm}%</span>
                        <span className="text-gray-800">{rpm} RPM</span>
                      </div>
                    </div>
                  );
                })}
              </div>
              
              <div className="mt-6 flex space-x-4">
                <button
                  onClick={handleApplyManualControl}
                  disabled={saving}
                  className="flex-1 bg-purple-500 text-white py-3 px-6 rounded-lg hover:bg-purple-600 transition disabled:opacity-50 flex items-center justify-center space-x-2"
                >
                  <Save className="w-5 h-5" />
                  <span>{saving ? 'Застосування...' : 'Застосувати зміни'}</span>
                </button>
                
                <button
                  onClick={() => applyProfile('balanced')}
                  className="bg-gray-300 text-gray-700 py-3 px-6 rounded-lg hover:bg-gray-400 transition flex items-center space-x-2"
                >
                  <RotateCcw className="w-5 h-5" />
                  <span>Скинути</span>
                </button>
              </div>
            </div>
          </>
        )}

        {/* Історія дій */}
        {actions.length > 0 && (
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-bold mb-4">📜 Історія дій користувача</h2>
            
            <div className="space-y-2">
              {actions.map((action, idx) => (
                <div key={idx} className="flex items-start space-x-3 text-sm border-b pb-2">
                  <span className="text-gray-700">
                    {new Date(action.timestamp).toLocaleTimeString('uk-UA')}
                  </span>
                  <span className="font-medium">{action.action}</span>
                  <span className="text-gray-800 flex-1">
                    {JSON.stringify(action.details)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Аргументация 
        <div className="bg-blue-50 border-l-4 border-blue-500 p-6 rounded-lg mt-6">
          <h3 className="font-bold text-lg mb-2">💡 Навіщо потрібен ручний режим?</h3>
          <ul className="space-y-2 text-sm text-gray-900">
            <li><strong>• Тестування:</strong> Перевірка працездатності кожного вентилятора</li>
            <li><strong>• Екстрені ситуації:</strong> Втручання при збоях алгоритму</li>
            <li><strong>• Спеціальні режими:</strong> Нічний режим (тиша), стрес-тести</li>
            <li><strong>• Економія енергії:</strong> Зниження обертів у простої нижче автоматичного мінімуму</li>
            <li><strong>• Знос обладнання:</strong> Перерозподіл навантаження між вентиляторами</li>
            <li><strong>• Демонстрація:</strong> Порівняння ефективності ручного vs автоматичного режиму</li>
          </ul>
        </div>
        */}
        
      </div>
    </div>
  );
}