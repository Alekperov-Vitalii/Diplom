'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { ArrowLeft, AlertTriangle, Power, Save, RotateCcw } from 'lucide-react';
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
        // fanPWM НЕ сбрасываем!
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

  // Инициализация PWM только при первом рендере
  useEffect(() => {
    if (Object.keys(fanPWM).length === 0) {
      const initialPWM: { [key: number]: number } = {};
      for (let i = 1; i <= 8; i++) {
        initialPWM[i] = 20;
      }
      setFanPWM(initialPWM);
    }
  }, []);

  const handleModeSwitch = async (newMode: 'auto' | 'manual') => {
    try {
      await setSystemMode(newMode);
      setMode({ ...mode!, mode: newMode });
      
      if (newMode === 'auto') {
        alert('✓ Система переключена на автоматический режим');
      }
    } catch (error) {
      alert('Ошибка переключения режима: ' + error);
    }
  };

  const handleApplyManualControl = async () => {
    if (mode?.mode !== 'manual') {
      alert('Сначала переключитесь на ручной режим!');
      return;
    }

    // Проверка: предупреждение о горячих GPU
    const warnings = [];
    for (let i = 1; i <= 8; i++) {
      const gpuTemp = state?.gpu_temps.find(g => g.gpu_id === i)?.temperature || 0;
      const pwm = fanPWM[i];
      
      if (gpuTemp > 70 && pwm < 60) {
        warnings.push(`GPU ${i}: ${gpuTemp.toFixed(1)}°C, но PWM только ${pwm}%`);
      }
    }

    if (warnings.length > 0) {
      const confirmed = confirm(
        '⚠️ ПРЕДУПРЕЖДЕНИЕ:\n\n' +
        warnings.join('\n') +
        '\n\nГПУ могут перегреться. Продолжить?'
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
      alert('✓ Ручные команды применены успешно!');
      
      // Обновляем историю действий
      const newActions = await getUserActions(10);
      setActions(newActions);
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : String(error);
      alert('Ошибка: ' + message);
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
    for (let i = 1; i <= 8; i++) {
      newPWM[i] = profiles[profile];
    }
    setFanPWM(newPWM);
  };

  if (loading) return <div className="p-8">Загрузка...</div>;

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-6xl mx-auto">
        <Link href="/" className="flex items-center text-blue-500 hover:text-blue-600 mb-4">
          <ArrowLeft className="w-4 h-4 mr-1" />
          Назад к Dashboard
        </Link>
        
        <h1 className="text-3xl font-bold mb-6">🎛️ Ручное управление вентиляторами</h1>
        
        {/* Переключатель режима */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h2 className="text-xl font-bold mb-4">Режим работы системы</h2>
          
          <div className="flex space-x-4 mb-4">
            <button
              onClick={() => handleModeSwitch('auto')}
              className={`flex-1 py-3 px-6 rounded-lg font-medium transition ${
                mode?.mode === 'auto'
                  ? 'bg-blue-500 text-white'
                  : 'bg-gray-200 hover:bg-gray-300'
              }`}
            >
              🤖 Автоматический (рекомендуется)
            </button>
            
            <button
              onClick={() => handleModeSwitch('manual')}
              className={`flex-1 py-3 px-6 rounded-lg font-medium transition ${
                mode?.mode === 'manual'
                  ? 'bg-purple-500 text-white'
                  : 'bg-gray-200 hover:bg-gray-300'
              }`}
            >
              🎛️ Ручной
            </button>
          </div>
          
          {mode?.mode === 'auto' && (
            <div className="bg-blue-50 border-l-4 border-blue-500 p-4 rounded">
              <p className="text-sm text-blue-700">
                ✓ Система работает в автоматическом режиме. Каскадный алгоритм управляет вентиляторами на основе температуры GPU и помещения.
              </p>
            </div>
          )}
          
          {mode?.mode === 'manual' && (
            <div className="bg-yellow-50 border-l-4 border-yellow-500 p-4 rounded">
              <div className="flex items-start">
                <AlertTriangle className="w-5 h-5 text-yellow-600 mr-2 flex-shrink-0 mt-0.5" />
                <div className="text-sm text-yellow-700">
                  <p className="font-medium mb-1">Ручной режим активен</p>
                  <p>Вы полностью контролируете вентиляторы. Следите за температурами GPU чтобы избежать перегрева.</p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Ручное управление */}
        {mode?.mode === 'manual' && (
          <>
            {/* Профили */}
            <div className="bg-white rounded-lg shadow p-6 mb-6">
              <h2 className="text-xl font-bold mb-4">Предустановленные профили</h2>
              
              <div className="grid grid-cols-3 gap-4">
                <button
                  onClick={() => applyProfile('quiet')}
                  className="p-4 border-2 border-gray-300 rounded-lg hover:border-green-500 transition"
                >
                  <div className="text-2xl mb-2">🔇</div>
                  <div className="font-medium">Тихий режим</div>
                  <div className="text-sm text-gray-600">25% PWM</div>
                </button>
                
                <button
                  onClick={() => applyProfile('balanced')}
                  className="p-4 border-2 border-gray-300 rounded-lg hover:border-blue-500 transition"
                >
                  <div className="text-2xl mb-2">⚖️</div>
                  <div className="font-medium">Сбалансированный</div>
                  <div className="text-sm text-gray-600">50% PWM</div>
                </button>
                
                <button
                  onClick={() => applyProfile('max')}
                  className="p-4 border-2 border-gray-300 rounded-lg hover:border-red-500 transition"
                >
                  <div className="text-2xl mb-2">🔥</div>
                  <div className="font-medium">Максимум</div>
                  <div className="text-sm text-gray-600">100% PWM</div>
                </button>
              </div>
            </div>

            {/* Слайдеры */}
            <div className="bg-white rounded-lg shadow p-6 mb-6">
              <h2 className="text-xl font-bold mb-4">Настройка вентиляторов</h2>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {[1, 2, 3, 4, 5, 6, 7, 8].map(fanId => {
                  const gpuTemp = state?.gpu_temps.find(g => g.gpu_id === fanId)?.temperature || 0;
                  const pwm = fanPWM[fanId] || 20;
                  const rpm = Math.round(800 + (5000 - 800) * pwm / 100);
                  const isWarning = gpuTemp > 70 && pwm < 60;
                  
                  return (
                    <div key={fanId} className="border rounded-lg p-4">
                      <div className="flex justify-between items-center mb-2">
                        <span className="font-medium">Вентилятор {fanId}</span>
                        <span className="text-sm text-gray-600">
                          GPU: {gpuTemp.toFixed(1)}°C
                        </span>
                      </div>
                      
                      {isWarning && (
                        <div className="bg-yellow-50 text-yellow-700 text-xs p-2 rounded mb-2">
                          ⚠️ GPU горячий, рекомендуется &gt;60% PWM
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
                        <span className="text-gray-600">PWM: {pwm}%</span>
                        <span className="text-gray-600">{rpm} RPM</span>
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
                  <span>{saving ? 'Применение...' : 'Применить изменения'}</span>
                </button>
                
                <button
                  onClick={() => applyProfile('balanced')}
                  className="bg-gray-300 text-gray-700 py-3 px-6 rounded-lg hover:bg-gray-400 transition flex items-center space-x-2"
                >
                  <RotateCcw className="w-5 h-5" />
                  <span>Сбросить</span>
                </button>
              </div>
            </div>
          </>
        )}

        {/* История действий */}
        {actions.length > 0 && (
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-bold mb-4">📜 История действий пользователя</h2>
            
            <div className="space-y-2">
              {actions.map((action, idx) => (
                <div key={idx} className="flex items-start space-x-3 text-sm border-b pb-2">
                  <span className="text-gray-500">
                    {new Date(action.timestamp).toLocaleTimeString('ru-RU')}
                  </span>
                  <span className="font-medium">{action.action}</span>
                  <span className="text-gray-600 flex-1">
                    {JSON.stringify(action.details)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Аргументация */}
        <div className="bg-blue-50 border-l-4 border-blue-500 p-6 rounded-lg mt-6">
          <h3 className="font-bold text-lg mb-2">💡 Зачем нужен ручной режим?</h3>
          <ul className="space-y-2 text-sm text-gray-700">
            <li><strong>• Тестирование:</strong> Проверка работоспособности каждого вентилятора</li>
            <li><strong>• Экстренные ситуации:</strong> Вмешательство при сбоях алгоритма</li>
            <li><strong>• Специальные режимы:</strong> Ночной режим (тишина), стресс-тесты</li>
            <li><strong>• Экономия энергии:</strong> Снижение оборотов в простое ниже автоматического минимума</li>
            <li><strong>• Износ оборудования:</strong> Перераспределение нагрузки между вентиляторами</li>
            <li><strong>• Демонстрация:</strong> Сравнение эффективности ручного vs автоматического режима</li>
          </ul>
        </div>
      </div>
    </div>
  );
}