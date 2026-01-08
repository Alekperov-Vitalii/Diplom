'use client';

import { Fan, Activity, Clock } from 'lucide-react';
import { FanStatistics } from '@/lib/api';

interface FanCardProps {
  stats: FanStatistics;
  gpuTemp: number;
  workload: number;
  mode: 'auto' | 'manual';
}

export default function FanCard({ stats, gpuTemp, workload, mode }: FanCardProps) {
  const { fan_id, current_pwm, current_rpm, avg_pwm_last_hour, time_on_high } = stats;
  
  // Визначаємо колір на основі PWM
  const getStatusColor = (pwm: number) => {
    if (pwm < 40) return 'text-green-500';
    if (pwm < 70) return 'text-yellow-500';
    return 'text-red-500';
  };
  
  const getStatusText = (pwm: number) => {
    if (pwm < 40) return 'Низьке навантаження';
    if (pwm < 70) return 'Середнє навантаження';
    return 'Високе навантаження';
  };
  
  const statusColor = getStatusColor(current_pwm);
  const statusText = getStatusText(current_pwm);
  
  // Форматуємо час на максимумі
  const formatTime = (seconds: number) => {
    const minutes = Math.floor(seconds / 60);
    const secs = seconds % 60;
    if (minutes === 0) return `${secs}с`;
    return `${minutes}хв ${secs}с`;
  };
  
  return (
    <div className="bg-white rounded-lg shadow-md p-5 border-l-4 border-blue-500 text-gray-900">
      {/* Заголовок */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-2">
          <Fan className={`w-6 h-6 ${statusColor}`} />
          <h3 className="text-lg font-bold">Вентилятор {fan_id}</h3>
        </div>
        <div className={`text-sm font-medium ${mode === 'auto' ? 'text-blue-600' : 'text-purple-600'}`}>
          {mode === 'auto' ? '🤖 Авто' : '🎛️ Ручний'}
        </div>
      </div>
      
      {/* GPU температура и нагрузка */}
      <div className="mb-3 text-sm text-gray-800">
        <div>GPU {fan_id}: <span className="font-semibold">{gpuTemp.toFixed(1)}°C</span></div>
        <div className="mt-1">
          <div className="flex justify-between text-xs mb-1">
            <span>Нагрузка</span>
            <span className="font-bold">{(workload * 100).toFixed(0)}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className={`h-2 rounded-full transition-all duration-300 ${
                workload < 0.3 ? 'bg-blue-400' :
                workload < 0.7 ? 'bg-orange-400' : 'bg-red-500'
              }`}
              style={{ width: `${workload * 100}%` }}
            />
          </div>
        </div>
      </div>
      
      {/* PWM шкала */}
      <div className="mb-3">
        <div className="flex justify-between text-xs text-gray-800 mb-1">
          <span>PWM</span>
          <span className="font-bold">{current_pwm}%</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-3">
          <div
            className={`h-3 rounded-full transition-all duration-300 ${
              current_pwm < 40 ? 'bg-green-500' :
              current_pwm < 70 ? 'bg-yellow-500' : 'bg-red-500'
            }`}
            style={{ width: `${current_pwm}%` }}
          />
        </div>
      </div>
      
      {/* RPM */}
      <div className="flex items-center justify-between mb-3 pb-3 border-b">
        <div className="flex items-center space-x-2">
          <Activity className="w-4 h-4 text-gray-700" />
          <span className="text-sm text-gray-800">Оберти</span>
        </div>
        <span className="text-sm font-semibold">{current_rpm.toLocaleString()} RPM</span>
      </div>
      
      {/* Статистика */}
      <div className="space-y-2 text-xs">
        <div className="flex justify-between">
          <span className="text-gray-800">Середній PWM (1год):</span>
          <span className="font-medium">{avg_pwm_last_hour.toFixed(1)}%</span>
        </div>
        
        <div className="flex justify-between items-center">
          <span className="text-gray-800 flex items-center">
            <Clock className="w-3 h-3 mr-1" />
            На максимумі (&gt;80%):
          </span>
          <span className="font-medium">{formatTime(time_on_high)}</span>
        </div>
        
        <div className="flex justify-between">
          <span className="text-gray-800">Статус:</span>
          <span className={`font-medium ${statusColor}`}>{statusText}</span>
        </div>
      </div>
    </div>
  );
}