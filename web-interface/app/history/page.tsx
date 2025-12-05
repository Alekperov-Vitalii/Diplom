'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { getHistory, HistoryDataPoint, getFanHistory, FanHistoryDataPoint } from '@/lib/api';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { ArrowLeft, Thermometer, Fan } from 'lucide-react';

interface ChartDataPoint {
  time: string;
  [key: string]: string | number;
}

export default function History() {
  const [tempData, setTempData] = useState<ChartDataPoint[]>([]);
  const [fanPWMData, setFanPWMData] = useState<ChartDataPoint[]>([]);
  const [fanRPMData, setFanRPMData] = useState<ChartDataPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [hours, setHours] = useState(1);
  const [activeChart, setActiveChart] = useState<'pwm' | 'rpm'>('pwm');

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        // Загружаем температуры
        const tempHistory = await getHistory(hours);
        
        // Группируем данные по времени
        const tempGrouped = tempHistory.reduce((acc: Record<string, ChartDataPoint>, point: HistoryDataPoint) => {
          const time = new Date(point.time).toLocaleTimeString('ru-RU', { 
            hour: '2-digit', 
            minute: '2-digit' 
          });
          
          if (!acc[time]) {
            acc[time] = { time };
          }
          
          if (point.measurement === 'gpu_temps' && point.gpu_id) {
            acc[time][`GPU ${point.gpu_id}`] = point.value;
          } else if (point.measurement === 'room_temp') {
            acc[time]['Комната'] = point.value;
          }
          
          return acc;
        }, {});
        
        setTempData(Object.values(tempGrouped));

        // Загружаем данные вентиляторов
        const fanHistory = await getFanHistory(hours);
        
        // Группируем PWM по времени
        const pwmGrouped = fanHistory
          .filter(p => p.field === 'pwm_duty')
          .reduce((acc: Record<string, ChartDataPoint>, point: FanHistoryDataPoint) => {
            const time = new Date(point.time).toLocaleTimeString('ru-RU', { 
              hour: '2-digit', 
              minute: '2-digit' 
            });
            
            if (!acc[time]) {
              acc[time] = { time };
            }
            
            acc[time][`Вентилятор ${point.fan_id}`] = point.value;
            
            return acc;
          }, {});
        
        setFanPWMData(Object.values(pwmGrouped));

        // Группируем RPM по времени
        const rpmGrouped = fanHistory
          .filter(p => p.field === 'rpm')
          .reduce((acc: Record<string, ChartDataPoint>, point: FanHistoryDataPoint) => {
            const time = new Date(point.time).toLocaleTimeString('ru-RU', { 
              hour: '2-digit', 
              minute: '2-digit' 
            });
            
            if (!acc[time]) {
              acc[time] = { time };
            }
            
            acc[time][`Вентилятор ${point.fan_id}`] = point.value;
            
            return acc;
          }, {});
        
        setFanRPMData(Object.values(rpmGrouped));
        
      } catch (error) {
        console.error('Error fetching history:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [hours]);

  if (loading) return <div className="p-8">Загрузка...</div>;

  // Цвета для линий GPU
  const gpuColors = [
    '#ef4444', // red
    '#f97316', // orange
    '#f59e0b', // amber
    '#eab308', // yellow
    '#84cc16', // lime
    '#22c55e', // green
    '#06b6d4', // cyan
    '#3b82f6', // blue
  ];

  // Цвета для линий вентиляторов
  const fanColors = [
    '#8b5cf6', // violet
    '#a855f7', // purple
    '#d946ef', // fuchsia
    '#ec4899', // pink
    '#f43f5e', // rose
    '#6366f1', // indigo
    '#0ea5e9', // sky
    '#14b8a6', // teal
  ];

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-7xl mx-auto">
        <div className="mb-6">
          <Link href="/" className="flex items-center text-blue-500 hover:text-blue-600 mb-4">
            <ArrowLeft className="w-4 h-4 mr-1" />
            Назад к Dashboard
          </Link>
          <h1 className="text-3xl font-bold">📊 История температур и работы вентиляторов</h1>
        </div>

        {/* Выбор периода */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <div className="flex items-center space-x-4 mb-4">
            <label className="font-medium">Период:</label>
            {[1, 3, 6, 24].map(h => (
              <button
                key={h}
                onClick={() => setHours(h)}
                className={`px-4 py-2 rounded ${
                  hours === h ? 'bg-blue-500 text-white' : 'bg-gray-200 hover:bg-gray-300'
                }`}
              >
                {h}ч
              </button>
            ))}
          </div>
        </div>

        {/* График температур GPU */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <div className="flex items-center space-x-2 mb-4">
            <Thermometer className="w-6 h-6 text-red-500" />
            <h2 className="text-xl font-bold">Температуры GPU</h2>
          </div>

          <ResponsiveContainer width="100%" height={400}>
            <LineChart data={tempData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis 
                dataKey="time" 
                tick={{ fontSize: 12 }}
                interval="preserveStartEnd"
              />
              <YAxis 
                label={{ value: 'Температура (°C)', angle: -90, position: 'insideLeft' }}
                domain={[20, 100]}
              />
              <Tooltip 
                contentStyle={{ backgroundColor: 'rgba(255, 255, 255, 0.95)', border: '1px solid #ccc' }}
                labelStyle={{ fontWeight: 'bold' }}
              />
              <Legend />
              {[1,2,3,4,5,6,7,8].map((id, idx) => (
                <Line 
                  key={id} 
                  type="monotone" 
                  dataKey={`GPU ${id}`} 
                  stroke={gpuColors[idx]} 
                  dot={false}
                  strokeWidth={2}
                />
              ))}
              <Line 
                type="monotone" 
                dataKey="Комната" 
                stroke="#000" 
                strokeWidth={3} 
                dot={false}
                strokeDasharray="5 5"
              />
            </LineChart>
          </ResponsiveContainer>

          <div className="mt-4 text-sm text-gray-600">
            <p>• Чёрная пунктирная линия — температура помещения</p>
            <p>• Цветные линии — температуры каждого GPU</p>
          </div>
        </div>

        {/* График работы вентиляторов */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center space-x-2">
              <Fan className="w-6 h-6 text-purple-500" />
              <h2 className="text-xl font-bold">Работа вентиляторов</h2>
            </div>
            
            {/* Переключатель PWM / RPM */}
            <div className="flex space-x-2">
              <button
                onClick={() => setActiveChart('pwm')}
                className={`px-4 py-2 rounded ${
                  activeChart === 'pwm' 
                    ? 'bg-purple-500 text-white' 
                    : 'bg-gray-200 hover:bg-gray-300'
                }`}
              >
                PWM (%)
              </button>
              <button
                onClick={() => setActiveChart('rpm')}
                className={`px-4 py-2 rounded ${
                  activeChart === 'rpm' 
                    ? 'bg-purple-500 text-white' 
                    : 'bg-gray-200 hover:bg-gray-300'
                }`}
              >
                RPM
              </button>
            </div>
          </div>

          {/* График PWM */}
          {activeChart === 'pwm' && (
            <>
              <ResponsiveContainer width="100%" height={400}>
                <LineChart data={fanPWMData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis 
                    dataKey="time" 
                    tick={{ fontSize: 12 }}
                    interval="preserveStartEnd"
                  />
                  <YAxis 
                    label={{ value: 'PWM (%)', angle: -90, position: 'insideLeft' }}
                    domain={[0, 100]}
                  />
                  <Tooltip 
                    contentStyle={{ backgroundColor: 'rgba(255, 255, 255, 0.95)', border: '1px solid #ccc' }}
                    labelStyle={{ fontWeight: 'bold' }}
                  />
                  <Legend />
                  {[1,2,3,4,5,6,7,8].map((id, idx) => (
                    <Line 
                      key={id} 
                      type="stepAfter"
                      dataKey={`Вентилятор ${id}`} 
                      stroke={fanColors[idx]} 
                      dot={false}
                      strokeWidth={2}
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>

              <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-4">
                {[1,2,3,4,5,6,7,8].map((id, idx) => (
                  <div key={id} className="flex items-center space-x-2">
                    <div 
                      className="w-4 h-4 rounded"
                      style={{ backgroundColor: fanColors[idx] }}
                    />
                    <span className="text-sm">Вентилятор {id}</span>
                  </div>
                ))}
              </div>

              <div className="mt-4 text-sm text-gray-600">
                <p>• Линии показывают изменение PWM (мощности) вентиляторов во времени</p>
                <p>• Ступенчатая форма графика отражает дискретные изменения управляющих команд</p>
                <p>• Чем выше линия, тем сильнее работал вентилятор в данный момент</p>
              </div>
            </>
          )}

          {/* График RPM */}
          {activeChart === 'rpm' && (
            <>
              <ResponsiveContainer width="100%" height={400}>
                <LineChart data={fanRPMData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis 
                    dataKey="time" 
                    tick={{ fontSize: 12 }}
                    interval="preserveStartEnd"
                  />
                  <YAxis 
                    label={{ value: 'Обороты (RPM)', angle: -90, position: 'insideLeft' }}
                    domain={[500, 5500]}
                  />
                  <Tooltip 
                    contentStyle={{ backgroundColor: 'rgba(255, 255, 255, 0.95)', border: '1px solid #ccc' }}
                    labelStyle={{ fontWeight: 'bold' }}
                  />
                  <Legend />
                  {[1,2,3,4,5,6,7,8].map((id, idx) => (
                    <Line 
                      key={id} 
                      type="stepAfter"
                      dataKey={`Вентилятор ${id}`} 
                      stroke={fanColors[idx]} 
                      dot={false}
                      strokeWidth={2}
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>

              <div className="mt-4 text-sm text-gray-600">
                <p>• Показывает фактические обороты (RPM) вентиляторов</p>
                <p>• Минимум: ~800 RPM (20% PWM), Максимум: ~5000 RPM (100% PWM)</p>
              </div>
            </>
          )}
        </div>

        {/* Аналитика */}
        <div className="bg-blue-50 border-l-4 border-blue-500 p-6 rounded-lg">
          <h3 className="font-bold text-lg mb-2">📈 Как читать графики</h3>
          <div className="space-y-2 text-sm text-gray-700">
            <p><strong>График температур:</strong> Показывает как GPU нагреваются под нагрузкой и остывают благодаря вентиляторам</p>
            <p><strong>График PWM вентиляторов:</strong> Демонстрирует работу адаптивного алгоритма — PWM увеличивается когда GPU греются</p>
            <p><strong>Корреляция:</strong> Сравните оба графика: когда температура GPU растёт → PWM вентилятора увеличивается через 30-60 секунд</p>
            <p><strong>Эффективность:</strong> Если GPU быстро остывает после увеличения PWM → система охлаждения работает эффективно</p>
          </div>
        </div>
      </div>
    </div>
  );
}