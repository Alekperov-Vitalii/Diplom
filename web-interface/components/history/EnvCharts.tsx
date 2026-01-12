'use client';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { HistoryChartDataPoint } from './constants';

interface Props {
  data: HistoryChartDataPoint[];
  height?: number;
}

export function HumidityChart({ data, height = 400 }: Props) {
  return (
    <>
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="time" tick={{ fontSize: 12 }} interval="preserveStartEnd" />
          <YAxis label={{ value: 'Вологість (%)', angle: -90, position: 'insideLeft' }} domain={[0, 100]} />
          <Tooltip 
            contentStyle={{ backgroundColor: 'rgba(255, 255, 255, 0.95)', border: '1px solid #ccc' }}
            labelStyle={{ fontWeight: 'bold' }}
            formatter={(value: number | string) => `${Number(value).toFixed(1)}%`}
          />
          <Legend />
          <Line type="monotone" dataKey="Вологість" stroke="#3b82f6" strokeWidth={3} dot={false} />
        </LineChart>
      </ResponsiveContainer>
      <div className="mt-2 text-sm text-gray-600">
        <p>• Оптимальний діапазон: 40-60%</p>
        <p>• Зелена зона: безпечна вологість</p>
      </div>
    </>
  );
}

export function DustChart({ data, height = 400 }: Props) {
  return (
    <>
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="time" tick={{ fontSize: 12 }} interval="preserveStartEnd" />
          <YAxis label={{ value: 'Пил (μg/m³)', angle: -90, position: 'insideLeft' }} domain={[0, 100]} />
          <Tooltip 
            contentStyle={{ backgroundColor: 'rgba(255, 255, 255, 0.95)', border: '1px solid #ccc' }}
            labelStyle={{ fontWeight: 'bold' }}
            formatter={(value: number | string) => `${Number(value).toFixed(1)} μg/m³`}
          />
          <Legend />
          <Line type="monotone" dataKey="Пил" stroke="#ef4444" strokeWidth={3} dot={false} />
        </LineChart>
      </ResponsiveContainer>
      <div className="mt-2 text-sm text-gray-600">
        <p>• Низький: &lt;25 μg/m³</p>
        <p>• Високий: &gt;50 μg/m³ (потрібне очищення)</p>
      </div>
    </>
  );
}

export function CiChart({ data, height = 400 }: Props) {
  return (
    <>
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="time" tick={{ fontSize: 12 }} interval="preserveStartEnd" />
          <YAxis domain={['auto', 'auto']} label={{ value: 'Index', angle: -90, position: 'insideLeft' }}/>
          <Tooltip labelStyle={{ fontWeight: 'bold' }} formatter={(val: number | string) => Number(val).toFixed(4)}/>
          <Legend />
          <Line type="monotone" dataKey="CI" stroke="#06b6d4" strokeWidth={2} dot={false} name="Corrosion Index" />
        </LineChart>
      </ResponsiveContainer>
      <div className="mt-2 text-sm text-gray-600">
        <p>• Індекс корозії (CI) на основі вологості</p>
      </div>
    </>
  );
}

export function FwiChart({ data, height = 400 }: Props) {
  return (
    <>
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="time" tick={{ fontSize: 12 }} interval="preserveStartEnd" />
          <YAxis domain={['auto', 'auto']} label={{ value: 'Index', angle: -90, position: 'insideLeft' }}/>
          <Tooltip labelStyle={{ fontWeight: 'bold' }} formatter={(val: number | string) => Number(val).toFixed(2)}/>
          <Legend />
          <Line type="monotone" dataKey="FWI" stroke="#6b7280" strokeWidth={2} dot={false} name="Fan Wear Index" />
        </LineChart>
      </ResponsiveContainer>
      <div className="mt-2 text-sm text-gray-600">
        <p>• Iндекс зносу вентиляторів (FWI) на основі пилу та обертів</p>
      </div>
    </>
  );
}
