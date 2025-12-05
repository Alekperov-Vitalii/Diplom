'use client';

import { Fan, Activity, Clock, Zap } from 'lucide-react';
import { FanStatistics } from '@/lib/api';

interface FanCardProps {
  stats: FanStatistics;
  gpuTemp: number;
  mode: 'auto' | 'manual';
}

export default function FanCard({ stats, gpuTemp, mode }: FanCardProps) {
  const { fan_id, current_pwm, current_rpm, avg_pwm_last_hour, time_on_high } = stats;
  
  // Определяем цвет на основе PWM
  const getStatusColor = (pwm: number) => {
    if (pwm < 40) return 'text-green-500';
    if (pwm < 70) return 'text-yellow-500';
    return 'text-red-500';
  };
  
  const getStatusText = (pwm: number) => {
    if (pwm < 40) return 'Низкая нагрузка';
    if (pwm < 70) return 'Средняя нагрузка';
    return 'Высокая нагрузка';
  };
  
  const statusColor = getStatusColor(current_pwm);
  const statusText = getStatusText(current_pwm);
  
  // Форматируем время на максимуме
  const formatTime = (seconds: number) => {
    const minutes = Math.floor(seconds / 60);
    const secs = seconds % 60;
    if (minutes === 0) return `${secs}с`;
    return `${minutes}м ${secs}с`;
  };
  
  return (
    <div className="bg-white rounded-lg shadow-md p-5 border-l-4 border-blue-500">
      {/* Заголовок */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-2">
          <Fan className={`w-6 h-6 ${statusColor}`} />
          <h3 className="text-lg font-bold">Вентилятор {fan_id}</h3>
        </div>
        <div className={`text-sm font-medium ${mode === 'auto' ? 'text-blue-600' : 'text-purple-600'}`}>
          {mode === 'auto' ? '🤖 Авто' : '🎛️ Ручной'}
        </div>
      </div>
      
      {/* GPU температура */}
      <div className="mb-3 text-sm text-gray-600">
        GPU {fan_id}: <span className="font-semibold">{gpuTemp.toFixed(1)}°C</span>
      </div>
      
      {/* PWM шкала */}
      <div className="mb-3">
        <div className="flex justify-between text-xs text-gray-600 mb-1">
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
          <Activity className="w-4 h-4 text-gray-500" />
          <span className="text-sm text-gray-600">Обороты</span>
        </div>
        <span className="text-sm font-semibold">{current_rpm.toLocaleString()} RPM</span>
      </div>
      
      {/* Статистика */}
      <div className="space-y-2 text-xs">
        <div className="flex justify-between">
          <span className="text-gray-600">Средний PWM (1ч):</span>
          <span className="font-medium">{avg_pwm_last_hour.toFixed(1)}%</span>
        </div>
        
        <div className="flex justify-between items-center">
          <span className="text-gray-600 flex items-center">
            <Clock className="w-3 h-3 mr-1" />
            На максимуме (&gt;80%):
          </span>
          <span className="font-medium">{formatTime(time_on_high)}</span>
        </div>
        
        <div className="flex justify-between">
          <span className="text-gray-600">Статус:</span>
          <span className={`font-medium ${statusColor}`}>{statusText}</span>
        </div>
      </div>
    </div>
  );
}