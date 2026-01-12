'use client';
import { useState } from 'react';
import { ComposedChart, Line, Area, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { HistoryChartDataPoint } from './constants';

interface Props {
  data: HistoryChartDataPoint[];
  height?: number;
}

export function CorrelationChart({ data, height = 400 }: Props) {
  const [mode, setMode] = useState<'temp-pwm' | 'humidity-dust' | 'dust-temp' | 'humidity-temp'>('temp-pwm');

  return (
    <>
      <div className="flex flex-wrap gap-2 mb-4">
        {[
            { id: 'temp-pwm', label: 'Temp vs PWM' },
            { id: 'humidity-dust', label: 'Hum vs Dust' },
            { id: 'dust-temp', label: 'Dust vs Temp' },
            { id: 'humidity-temp', label: 'Hum vs Temp' }
        ].map(m => (
            <button
                key={m.id}
                onClick={() => setMode(m.id as any)}
                className={`px-3 py-1 text-sm rounded border transition-colors ${
                    mode === m.id 
                    ? 'bg-indigo-500 text-white border-indigo-600 shadow-sm' 
                    : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
                }`}
            >
                {m.label}
            </button>
        ))}
      </div>

      <p className="text-sm text-gray-500 mb-4 h-5">
        {mode === 'temp-pwm' && "Порівняння температури GPU та роботи вентиляторів."}
        {mode === 'humidity-dust' && "Взаємозв'язок вологості та запиленості."}
        {mode === 'dust-temp' && "Вплив запиленості на температуру."}
        {mode === 'humidity-temp' && "Вплив вологості на ефективність охолодження."}
      </p>

      <ResponsiveContainer width="100%" height={height}>
        <ComposedChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="time" tick={{ fontSize: 12 }} />
          
          {mode === 'temp-pwm' && (
              <>
                <YAxis yAxisId="left" label={{ value: 'Температура (°C)', angle: -90, position: 'insideLeft' }} domain={[20, 100]} />
                <YAxis yAxisId="right" orientation="right" label={{ value: 'PWM (%)', angle: 90, position: 'insideRight' }} domain={[0, 100]} />
                <Line yAxisId="left" type="monotone" dataKey="AvgTemp" stroke="#ef4444" strokeWidth={3} name="Avg GPU Temp" dot={false} />
                <Area yAxisId="right" type="monotone" dataKey="AvgPWM" fill="#8884d8" stroke="#8884d8" fillOpacity={0.3} name="Avg Fan PWM" />
              </>
          )}

          {mode === 'humidity-dust' && (
              <>
                <YAxis yAxisId="left" label={{ value: 'Вологість (%)', angle: -90, position: 'insideLeft' }} domain={[0, 100]} />
                <YAxis yAxisId="right" orientation="right" label={{ value: 'Пил (μg/m³)', angle: 90, position: 'insideRight' }} domain={[0, 100]} />
                <Line yAxisId="left" type="monotone" dataKey="Humidity" stroke="#3b82f6" strokeWidth={3} name="Вологість" dot={false} />
                <Area yAxisId="right" type="monotone" dataKey="Dust" fill="#fbbf24" stroke="#fbbf24" fillOpacity={0.3} name="Пил" />
              </>
          )}

          {mode === 'dust-temp' && (
              <>
                <YAxis yAxisId="left" label={{ value: 'Пил (μg/m³)', angle: -90, position: 'insideLeft' }} domain={[0, 100]} />
                <YAxis yAxisId="right" orientation="right" label={{ value: 'Температура (°C)', angle: 90, position: 'insideRight' }} domain={[20, 100]} />
                <Area yAxisId="left" type="monotone" dataKey="Dust" fill="#fbbf24" stroke="#fbbf24" fillOpacity={0.3} name="Пил" />
                <Line yAxisId="right" type="monotone" dataKey="AvgTemp" stroke="#ef4444" strokeWidth={3} name="Avg GPU Temp" dot={false} />
              </>
          )}

          {mode === 'humidity-temp' && (
              <>
                <YAxis yAxisId="left" label={{ value: 'Вологість (%)', angle: -90, position: 'insideLeft' }} domain={[0, 100]} />
                <YAxis yAxisId="right" orientation="right" label={{ value: 'Температура (°C)', angle: 90, position: 'insideRight' }} domain={[20, 100]} />
                <Area yAxisId="left" type="monotone" dataKey="Humidity" fill="#3b82f6" stroke="#3b82f6" fillOpacity={0.3} name="Вологість" />
                <Line yAxisId="right" type="monotone" dataKey="AvgTemp" stroke="#ef4444" strokeWidth={3} name="Avg GPU Temp" dot={false} />
              </>
          )}

          <Tooltip labelStyle={{ fontWeight: 'bold' }} contentStyle={{ backgroundColor: 'rgba(255, 255, 255, 0.95)', border: '1px solid #ccc' }}/>
          <Legend />
        </ComposedChart>
      </ResponsiveContainer>
    </>
  );
}
