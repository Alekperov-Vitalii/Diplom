'use client';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { fanColors, HistoryChartDataPoint } from './constants';

interface Props {
  data: HistoryChartDataPoint[];
  height?: number;
}

export function FanPwmChart({ data, height = 400 }: Props) {
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
            label={{ value: 'PWM (%)', angle: -90, position: 'insideLeft' }}
            domain={[0, 100]}
          />
          <Tooltip 
            contentStyle={{ backgroundColor: 'rgba(255, 255, 255, 0.95)', border: '1px solid #ccc' }}
            labelStyle={{ fontWeight: 'bold' }}
            formatter={(value: number | string) => `${Number(value).toFixed(0)}%`}
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
      </div>
    </>
  );
}

export function FanRpmChart({ data, height = 400 }: Props) {
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
            label={{ value: 'Оберти (RPM)', angle: -90, position: 'insideLeft' }}
            domain={[500, 5500]}
          />
          <Tooltip 
            contentStyle={{ backgroundColor: 'rgba(255, 255, 255, 0.95)', border: '1px solid #ccc' }}
            labelStyle={{ fontWeight: 'bold' }}
            formatter={(value: number | string) => `${Number(value).toFixed(0)} RPM`}
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
  );
}
