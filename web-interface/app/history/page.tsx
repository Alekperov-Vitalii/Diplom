'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { getHistory, HistoryDataPoint, getFanHistory, FanHistoryDataPoint, getEnvironmentalHistory, EnvironmentalHistoryPoint, getAdvancedTrendsHistory, AdvancedTrendHistoryPoint } from '@/lib/api';
import { ArrowLeft, Thermometer, Fan, Droplets, Activity, TrendingUp, Cloud, AlertTriangle, LayoutGrid, Square } from 'lucide-react';

import { HistoryChartDataPoint } from '@/components/history/constants';
import { GpuTempChart } from '@/components/history/GpuTempChart';
import { FanPwmChart, FanRpmChart } from '@/components/history/FanCharts';
import { HumidityChart, DustChart, CiChart, FwiChart } from '@/components/history/EnvCharts';
import { CorrelationChart } from '@/components/history/CorrelationChart';

export default function History() {
  const [tempData, setTempData] = useState<HistoryChartDataPoint[]>([]);
  const [fanPWMData, setFanPWMData] = useState<HistoryChartDataPoint[]>([]);
  const [fanRPMData, setFanRPMData] = useState<HistoryChartDataPoint[]>([]);
  const [humidityData, setHumidityData] = useState<HistoryChartDataPoint[]>([]);
  const [dustData, setDustData] = useState<HistoryChartDataPoint[]>([]);
  const [advTrendData, setAdvTrendData] = useState<HistoryChartDataPoint[]>([]);
  const [correlationData, setCorrelationData] = useState<HistoryChartDataPoint[]>([]);
  
  const [loading, setLoading] = useState(true);
  const [hours, setHours] = useState(1);
  const [viewMode, setViewMode] = useState<'single' | 'grid'>('single');
  const [activeTrend, setActiveTrend] = useState<string>('gpu-temp');

  const trendsList = [
    { id: 'gpu-temp', label: 'Температури GPU', icon: Thermometer, color: 'text-red-500' },
    { id: 'fan-pwm', label: 'Вентилятори (PWM)', icon: Fan, color: 'text-purple-500' },
    { id: 'fan-rpm', label: 'Вентилятори (RPM)', icon: Fan, color: 'text-indigo-500' },
    { id: 'humidity', label: 'Вологість', icon: Droplets, color: 'text-blue-500' },
    { id: 'dust', label: 'Пил', icon: Cloud, color: 'text-amber-500' },
    { id: 'ci', label: 'Корозія (CI)', icon: AlertTriangle, color: 'text-cyan-500' },
    { id: 'fwi', label: 'Знос вентиляторів (FWI)', icon: Activity, color: 'text-gray-500' },
    { id: 'correlation', label: 'Кореляція (Overlay)', icon: TrendingUp, color: 'text-green-500' },
  ];

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        const tempHistory = await getHistory(hours);
        const tempGrouped = tempHistory.reduce((acc: Record<string, HistoryChartDataPoint>, point: HistoryDataPoint) => {
          const time = new Date(point.time).toLocaleTimeString('uk-UA', { hour: '2-digit', minute: '2-digit' });
          if (!acc[time]) acc[time] = { time };
          if (point.measurement === 'gpu_temps' && point.gpu_id) {
            acc[time][`GPU ${point.gpu_id}`] = point.value;
          } else if (point.measurement === 'room_temp') {
            acc[time]['Кімната'] = point.value;
          }
          return acc;
        }, {});
        setTempData(Object.values(tempGrouped));

        const fanHistory = await getFanHistory(hours);
        const pwmGrouped = fanHistory
          .filter(p => p.field === 'pwm_duty')
          .reduce((acc: Record<string, HistoryChartDataPoint>, point: FanHistoryDataPoint) => {
            const time = new Date(point.time).toLocaleTimeString('uk-UA', { hour: '2-digit', minute: '2-digit' });
            if (!acc[time]) acc[time] = { time };
            acc[time][`Вентилятор ${point.fan_id}`] = point.value;
            return acc;
          }, {});
        setFanPWMData(Object.values(pwmGrouped));

        const rpmGrouped = fanHistory
          .filter(p => p.field === 'rpm')
          .reduce((acc: Record<string, HistoryChartDataPoint>, point: FanHistoryDataPoint) => {
            const time = new Date(point.time).toLocaleTimeString('uk-UA', { hour: '2-digit', minute: '2-digit' });
            if (!acc[time]) acc[time] = { time };
            acc[time][`Вентилятор ${point.fan_id}`] = point.value;
            return acc;
          }, {});
        setFanRPMData(Object.values(rpmGrouped));
        
        const envHistory = await getEnvironmentalHistory(hours);
        const humidityGrouped = envHistory
          .filter(p => p.field === 'humidity')
          .reduce((acc: Record<string, HistoryChartDataPoint>, point: EnvironmentalHistoryPoint) => {
            const time = new Date(point.time).toLocaleTimeString('uk-UA', { hour: '2-digit', minute: '2-digit' });
            if (!acc[time]) acc[time] = { time };
            acc[time]['Вологість'] = point.value;
            return acc;
          }, {});
        setHumidityData(Object.values(humidityGrouped));
        
        const dustGrouped = envHistory
          .filter(p => p.field === 'dust')
          .reduce((acc: Record<string, HistoryChartDataPoint>, point: EnvironmentalHistoryPoint) => {
            const time = new Date(point.time).toLocaleTimeString('uk-UA', { hour: '2-digit', minute: '2-digit' });
            if (!acc[time]) acc[time] = { time };
            acc[time]['Пил'] = point.value;
            return acc;
          }, {});
        setDustData(Object.values(dustGrouped));

        const advHistory = await getAdvancedTrendsHistory(hours);
        const advGrouped = advHistory.reduce((acc: Record<string, HistoryChartDataPoint>, point: AdvancedTrendHistoryPoint) => {
            const time = new Date(point.time).toLocaleTimeString('uk-UA', { hour: '2-digit', minute: '2-digit' });
            if (!acc[time]) acc[time] = { time };
            acc[time]['CI'] = point.ci;
            acc[time]['FWI'] = point.fwi;
            return acc;
        }, {});
        setAdvTrendData(Object.values(advGrouped));

        const correlationMap: Record<string, any> = {};
        Object.values(tempGrouped).forEach((p: HistoryChartDataPoint) => {
            const time = p.time;
            let sum = 0; let count = 0;
            Object.keys(p).forEach(k => {
                if (k.startsWith('GPU') && typeof p[k] === 'number') {
                    sum += (p[k] as number); count++;
                }
            });
            if (!correlationMap[time]) correlationMap[time] = { time };
            if (count > 0) correlationMap[time]['AvgTemp'] = sum / count;
        });

        Object.values(pwmGrouped).forEach((p: HistoryChartDataPoint) => {
            const time = p.time;
            let sum = 0; let count = 0;
            Object.keys(p).forEach(k => {
                if (k.startsWith('Вентилятор') && typeof p[k] === 'number') {
                    sum += (p[k] as number); count++;
                }
            });
            if (correlationMap[time]) {
                if (count > 0) correlationMap[time]['AvgPWM'] = sum / count;
            }
        });

        Object.values(humidityGrouped).forEach((p: HistoryChartDataPoint) => {
             const time = p.time;
             if (correlationMap[time] && typeof p['Вологість'] === 'number') {
                 correlationMap[time]['Humidity'] = p['Вологість'];
             }
        });

        Object.values(dustGrouped).forEach((p: HistoryChartDataPoint) => {
             const time = p.time;
             if (correlationMap[time] && typeof p['Пил'] === 'number') {
                 correlationMap[time]['Dust'] = p['Пил'];
             }
        });
        
        setCorrelationData(Object.values(correlationMap).sort((a, b) => a.time.localeCompare(b.time)));

      } catch (error) {
        console.error('Error fetching history:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [hours]);

  const renderChart = (type: string, height: number = 400) => {
    switch(type) {
      case 'gpu-temp': return <GpuTempChart data={tempData} height={height} />;
      case 'fan-pwm': return <FanPwmChart data={fanPWMData} height={height} />;
      case 'fan-rpm': return <FanRpmChart data={fanRPMData} height={height} />;
      case 'humidity': return <HumidityChart data={humidityData} height={height} />;
      case 'dust': return <DustChart data={dustData} height={height} />;
      case 'ci': return <CiChart data={advTrendData} height={height} />;
      case 'fwi': return <FwiChart data={advTrendData} height={height} />;
      case 'correlation': return <CorrelationChart data={correlationData} height={height} />;
      default: return null;
    }
  };

  if (loading) return <div className="p-8">Завантаження...</div>;

  return (
    <div className="min-h-screen bg-gray-50 text-gray-900 p-8">
      <div className="max-w-screen-2xl mx-auto">
        <div className="flex flex-col md:flex-row md:items-center justify-between mb-6">
          <div>
            <Link href="/" className="flex items-center text-blue-500 hover:text-blue-600 mb-2">
              <ArrowLeft className="w-4 h-4 mr-1" />
              Назад до Dashboard
            </Link>
            <h1 className="text-3xl font-bold">📊 Історія та аналітика</h1>
          </div>
          
          <div className="flex items-center space-x-4 mt-4 md:mt-0">
             {/* Період */}
             <div className="bg-white rounded-lg shadow px-4 py-2 flex items-center space-x-2">
                <span className="text-sm font-medium text-gray-600">Період:</span>
                {[1, 3, 6, 24].map(h => (
                  <button
                    key={h}
                    onClick={() => setHours(h)}
                    className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                      hours === h ? 'bg-blue-500 text-white' : 'bg-gray-100 hover:bg-gray-200 text-gray-700'
                    }`}
                  >
                    {h}ч
                  </button>
                ))}
            </div>

            {/* View Mode */}
            <div className="bg-white rounded-lg shadow p-1 flex">
                <button
                    onClick={() => setViewMode('single')}
                    className={`p-2 rounded ${viewMode === 'single' ? 'bg-indigo-100 text-indigo-600' : 'text-gray-500 hover:bg-gray-50'}`}
                    title="Single View"
                >
                    <Square className="w-5 h-5" />
                </button>
                <button
                    onClick={() => setViewMode('grid')}
                    className={`p-2 rounded ${viewMode === 'grid' ? 'bg-indigo-100 text-indigo-600' : 'text-gray-500 hover:bg-gray-50'}`}
                    title="Grid View"
                >
                    <LayoutGrid className="w-5 h-5" />
                </button>
            </div>
          </div>
        </div>

        {viewMode === 'single' ? (
          <div className="flex flex-col lg:flex-row gap-6">
             {/* Sidebar Navigation */}
             <div className="lg:w-1/4">
                <div className="bg-white rounded-xl shadow-lg p-4 sticky top-6">
                    <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-3 px-2">Тренди</h3>
                    <div className="space-y-1">
                        {trendsList.map(trend => {
                            const Icon = trend.icon;
                            const isActive = activeTrend === trend.id;
                            return (
                                <button
                                    key={trend.id}
                                    onClick={() => setActiveTrend(trend.id)}
                                    className={`w-full flex items-center px-3 py-3 rounded-lg text-left transition-all duration-200 ${
                                        isActive 
                                        ? 'bg-blue-50 text-blue-700 shadow-sm ring-1 ring-blue-200' 
                                        : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900'
                                    }`}
                                >
                                    <Icon className={`w-5 h-5 mr-3 ${isActive ? 'text-blue-600' : trend.color}`} />
                                    <span className="font-medium">{trend.label}</span>
                                </button>
                            );
                        })}
                    </div>
                </div>
             </div>

             {/* Main Chart Area */}
             <div className="lg:w-3/4">
                <div className="bg-white rounded-xl shadow-lg p-6 min-h-[500px]">
                    <div className="flex items-center space-x-3 mb-6 border-b pb-4">
                        {(() => {
                            const active = trendsList.find(t => t.id === activeTrend);
                            const Icon = active?.icon || Activity;
                            return (
                                <>
                                    <div className={`p-2 rounded-lg bg-gray-100 ${active?.color}`}>
                                        <Icon className="w-6 h-6" />
                                    </div>
                                    <h2 className="text-2xl font-bold">{active?.label}</h2>
                                </>
                            );
                        })()}
                    </div>
                    
                    <div className="animate-in fade-in duration-300">
                        {renderChart(activeTrend, 500)}
                    </div>
                </div>
             </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
              {trendsList.map(trend => {
                  const Icon = trend.icon;
                  return (
                      <div key={trend.id} className="bg-white rounded-xl shadow-md p-4 flex flex-col hover:shadow-lg transition-shadow">
                          <div className="flex items-center space-x-2 mb-4">
                              <Icon className={`w-5 h-5 ${trend.color}`} />
                              <h3 className="font-bold text-gray-900">{trend.label}</h3>
                          </div>
                          <div className="flex-1">
                              {renderChart(trend.id, 250)}
                          </div>
                      </div>
                  );
              })}
          </div>
        )}
      </div>
    </div>
  );
}