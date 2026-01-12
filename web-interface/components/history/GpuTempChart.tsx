'use client';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { gpuColors, HistoryChartDataPoint } from './constants';

interface Props {
  data: HistoryChartDataPoint[];
  height?: number;
}

export function GpuTempChart({ data, height = 400 }: Props) {
  return (
    <>
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={data}>
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
            formatter={(value: number | string) => `${Number(value).toFixed(1)}°C`}
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
    </>
  );
}
