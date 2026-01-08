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
        // Завантажуємо температури
        const tempHistory = await getHistory(hours);
        
        // Групуємо дані за часом
        const tempGrouped = tempHistory.reduce((acc: Record<string, ChartDataPoint>, point: HistoryDataPoint) => {
          const time = new Date(point.time).toLocaleTimeString('uk-UA', { 
            hour: '2-digit', 
            minute: '2-digit' 
          });
          
          if (!acc[time]) {
            acc[time] = { time };
          }
          
          if (point.measurement === 'gpu_temps' && point.gpu_id) {
            acc[time][`GPU ${point.gpu_id}`] = point.value;
          } else if (point.measurement === 'room_temp') {
            acc[time]['Кімната'] = point.value;
          }
          
          return acc;
        }, {});
        
        setTempData(Object.values(tempGrouped));

        // Завантажуємо дані вентиляторів
        const fanHistory = await getFanHistory(hours);
        
        // Групуємо PWM за часом
        const pwmGrouped = fanHistory
          .filter(p => p.field === 'pwm_duty')
          .reduce((acc: Record<string, ChartDataPoint>, point: FanHistoryDataPoint) => {
            const time = new Date(point.time).toLocaleTimeString('uk-UA', { 
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

        // Групуємо RPM за часом
        const rpmGrouped = fanHistory
          .filter(p => p.field === 'rpm')
          .reduce((acc: Record<string, ChartDataPoint>, point: FanHistoryDataPoint) => {
            const time = new Date(point.time).toLocaleTimeString('uk-UA', { 
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

  if (loading) return <div className="p-8">Завантаження...</div>;

  // Кольори для ліній GPU (16 кольорів)
  const gpuColors = [
    '#ef4444', // red
    '#f97316', // orange
    '#f59e0b', // amber
    '#eab308', // yellow
    '#84cc16', // lime
    '#22c55e', // green
    '#06b6d4', // cyan
    '#3b82f6', // blue
    '#8b5cf6', // violet
    '#a855f7', // purple
    '#d946ef', // fuchsia
    '#ec4899', // pink
    '#f43f5e', // rose
    '#6366f1', // indigo
    '#0ea5e9', // sky
    '#14b8a6', // teal
  ];

  // Кольори для ліній вентиляторів (16 кольорів)
  const fanColors = [
    '#8b5cf6', // violet
    '#a855f7', // purple
    '#d946ef', // fuchsia
    '#ec4899', // pink
    '#f43f5e', // rose
    '#6366f1', // indigo
    '#0ea5e9', // sky
    '#14b8a6', // teal
    '#ef4444', // red
    '#f97316', // orange
    '#f59e0b', // amber
    '#eab308', // yellow
    '#84cc16', // lime
    '#22c55e', // green
    '#06b6d4', // cyan
    '#3b82f6', // blue
  ];

  return (
    <div className="min-h-screen bg-gray-50 text-gray-900 p-8">
      <div className="max-w-7xl mx-auto">
        <div className="mb-6">
          <Link href="/" className="flex items-center text-blue-500 hover:text-blue-600 mb-4">
            <ArrowLeft className="w-4 h-4 mr-1" />
            Назад до Dashboard
          </Link>
          <h1 className="text-3xl font-bold">📊 Історія температур та роботи вентиляторів</h1>
        </div>

        {/* Вибір періоду */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <div className="flex items-center space-x-4 mb-4">
            <label className="font-medium">Період:</label>
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

        {/* Графік температур GPU */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <div className="flex items-center space-x-2 mb-4">
            <Thermometer className="w-6 h-6 text-red-500" />
            <h2 className="text-xl font-bold">Температури GPU</h2>
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
                formatter={(value: number) => `${Number(value).toFixed(1)}°C`}
              />
              <Legend />
              {[1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16].map((id, idx) => (
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
                dataKey="Кімната" 
                stroke="#000" 
                strokeWidth={3} 
                dot={false}
                strokeDasharray="5 5"
              />
            </LineChart>
          </ResponsiveContainer>

          <div className="mt-4 text-sm text-gray-800">
            <p>• Чорна пунктирна лінія — температура приміщення</p>
            <p>• Кольорові лінії — температури кожного GPU</p>
          </div>
        </div>

        {/* Графік роботи вентиляторів */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center space-x-2">
              <Fan className="w-6 h-6 text-purple-500" />
              <h2 className="text-xl font-bold">Робота вентиляторів</h2>
            </div>
            
            {/* Перемикач PWM / RPM */}
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

          {/* Графік PWM */}
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
                    formatter={(value: number) => `${Number(value).toFixed(0)}%`}
                  />
                  <Legend />
                  {[1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16].map((id, idx) => (
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
                {[1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16].map((id, idx) => (
                  <div key={id} className="flex items-center space-x-2">
                    <div 
                      className="w-4 h-4 rounded"
                      style={{ backgroundColor: fanColors[idx] }}
                    />
                    <span className="text-sm">Вентилятор {id}</span>
                  </div>
                ))}
              </div>

              <div className="mt-4 text-sm text-gray-800">
                <p>• Лінії показують зміну PWM (потужності) вентиляторів у часі</p>
                <p>• Ступінчаста форма графіка відображає дискретні зміни керуючих команд</p>
                <p>• Чим вище лінія, тим сильніше працював вентилятор у даний момент</p>
              </div>
            </>
          )}

          {/* Графік RPM */}
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
                    label={{ value: 'Оберти (RPM)', angle: -90, position: 'insideLeft' }}
                    domain={[500, 5500]}
                  />
                  <Tooltip 
                    contentStyle={{ backgroundColor: 'rgba(255, 255, 255, 0.95)', border: '1px solid #ccc' }}
                    labelStyle={{ fontWeight: 'bold' }}
                    formatter={(value: number) => `${Number(value).toFixed(0)} RPM`}
                  />
                  <Legend />
                  {[1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16].map((id, idx) => (
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

              <div className="mt-4 text-sm text-gray-800">
                <p>• Показує фактичні оберти (RPM) вентиляторів</p>
                <p>• Мінімум: ~800 RPM (20% PWM), Максимум: ~5000 RPM (100% PWM)</p>
              </div>
            </>
          )}
        </div>

        {/* Аналітика */}
        <div className="bg-blue-50 border-l-4 border-blue-500 p-6 rounded-lg">
          <h3 className="font-bold text-lg mb-2">📈 Як читати графіки</h3>
          <div className="space-y-2 text-sm text-gray-900">
            <p><strong>Графік температур:</strong> Показує як GPU нагріваються під навантаженням і остигають завдяки вентиляторам</p>
            <p><strong>Графік PWM вентиляторів:</strong> Демонструє роботу адаптивного алгоритму — PWM збільшується коли GPU гріються</p>
            <p><strong>Кореляція:</strong> Порівняйте обидва графіки: коли температура GPU зростає → PWM вентилятора збільшується через 30-60 секунд</p>
            <p><strong>Ефективність:</strong> Якщо GPU швидко остигає після збільшення PWM → система охолодження працює ефективно</p>
          </div>
        </div>
      </div>
    </div>
  );
}