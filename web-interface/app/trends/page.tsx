'use client';

import { useEffect, useState } from 'react';
import { getEnvironmentalTrends, EnvironmentalTrends, getAdvancedTrends, AdvancedTrends } from '@/lib/api';
import { TrendingUp, Wind, Gauge, ArrowLeft, Droplets, Fan, AlertTriangle } from 'lucide-react';
import Link from 'next/link';

export default function TrendsPage() {
  const [trends, setTrends] = useState<EnvironmentalTrends | null>(null);
  const [advTrends, setAdvTrends] = useState<AdvancedTrends | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchTrends = async () => {
      try {

        const [trendsData, advData] = await Promise.all([
          getEnvironmentalTrends(),
          getAdvancedTrends()
        ]);
        setTrends(trendsData);
        setAdvTrends(advData);
      } catch (error) {
        console.error('Error fetching trends:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchTrends();
    const interval = setInterval(fetchTrends, 30000); // Update every 30s
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-xl">Завантаження...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 text-gray-900 p-8">
      <div className="max-w-7xl mx-auto">
        <Link href="/" className="flex items-center text-blue-500 hover:text-blue-600 mb-4">
          <ArrowLeft className="w-4 h-4 mr-1" />
          Назад до Dashboard
        </Link>
        <h1 className="text-4xl font-bold mb-8">Тренди навколишнього середовища</h1>

        {/* Trend 1: Humidity Change Rate */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <div className="flex items-center mb-4">
            <Wind className="w-6 h-6 mr-2 text-blue-500" />
            <h2 className="text-2xl font-bold">Швидкість зміни вологості (погодинна)</h2>
          </div>
          
          <div className="mb-4">
            <div className="text-sm text-gray-600 mb-2">
              Формула: <code className="bg-gray-100 px-2 py-1 rounded">{trends?.hourly_humidity_change_rate.formula}</code>
            </div>
            <div className="text-4xl font-bold text-blue-600">
              {trends?.hourly_humidity_change_rate.value?.toFixed(2) ?? 'N/A'} %/год
            </div>
            <div className="text-lg mt-2 text-gray-700">
              {trends?.hourly_humidity_change_rate.interpretation}
            </div>
          </div>
          
          <div className="text-sm text-gray-600">
            <p><strong>Інтерпретація:</strong></p>
            <ul className="list-disc ml-5 mt-2">
              <li>&gt;1%/год = Висока вентиляція (приплив)</li>
              <li>0-1%/год = Помірна вентиляція</li>
              <li>&lt;0%/год = Герметичний простір</li>
            </ul>
          </div>
        </div>

        {/* Trend 2: Dust Accumulation Rate */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <div className="flex items-center mb-4">
            <TrendingUp className="w-6 h-6 mr-2 text-orange-500" />
            <h2 className="text-2xl font-bold">Швидкість накопичення пилу (погодинна)</h2>
          </div>
          
          <div className="mb-4">
            <div className="text-sm text-gray-600 mb-2">
              Формула: <code className="bg-gray-100 px-2 py-1 rounded">{trends?.hourly_dust_accumulation_rate.formula}</code>
            </div>
            <div className="text-4xl font-bold text-orange-600">
              {trends?.hourly_dust_accumulation_rate.value?.toFixed(2) ?? 'N/A'} μg/m³/год
            </div>
            <div className="text-lg mt-2 text-gray-700">
              {trends?.hourly_dust_accumulation_rate.interpretation}
            </div>
          </div>
          
          <div className="text-sm text-gray-600">
            <p><strong>Інтерпретація:</strong></p>
            <ul className="list-disc ml-5 mt-2">
              <li>&gt;2 μg/m³/год = Погана фільтрація</li>
              <li>1-2 μg/m³/год = Помірна фільтрація</li>
              <li>&lt;1 μg/m³/год = Хороша фільтрація</li>
            </ul>
          </div>
        </div>

        {/* Trend 3: Cooling Efficiency Modifier */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <div className="flex items-center mb-4">
            <Gauge className="w-6 h-6 mr-2 text-green-500" />
            <h2 className="text-2xl font-bold">Модифікатор ефективності охолодження</h2>
          </div>
          
          <div className="mb-4">
            <div className="text-sm text-gray-600 mb-2">
              Формула: <code className="bg-gray-100 px-2 py-1 rounded">{trends?.cooling_efficiency_modifier.formula}</code>
            </div>
            <div className="text-4xl font-bold text-green-600">
              {trends?.cooling_efficiency_modifier.value?.toFixed(3) ?? 'N/A'}
            </div>
            <div className="text-lg mt-2 text-red-600">
              Зниження на {trends?.cooling_efficiency_modifier.reduction_percent?.toFixed(1)}%
            </div>
          </div>
          
          <div className="text-sm text-gray-600">
            <p><strong>Пояснення:</strong></p>
            <p className="mt-2">
              Цей коефіцієнт показує, наскільки ефективно працює охолодження GPU 
              з урахуванням поточних умов навколишнього середовища. Значення менше 1.0 
              означає, що вентилятори повинні працювати інтенсивніше для досягнення 
              тієї ж ефективності охолодження.
            </p>
          </div>
        </div>


        {/* --- ADVANCED TRENDS (CUMULATIVE) --- */}
        <h2 className="text-3xl font-bold mb-6 mt-12 border-b pb-2">Довгострокові показники зносу</h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
            {/* Corrosion Index Card */}
            <div className="bg-white rounded-lg shadow p-6 border-l-4 border-cyan-500">
                <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center">
                        <Droplets className="w-6 h-6 mr-2 text-cyan-600" />
                        <h2 className="text-xl font-bold">Індекс Корозії (CI)</h2>
                    </div>
                    <span className={`px-3 py-1 rounded-full text-sm font-bold ${
                        advTrends?.corrosion_index.risk_level === 'high' ? 'bg-red-100 text-red-700' :
                        advTrends?.corrosion_index.risk_level === 'medium' ? 'bg-yellow-100 text-yellow-700' :
                        'bg-green-100 text-green-700'
                    }`}>
                        {advTrends?.corrosion_index.risk_level.toUpperCase()}
                    </span>
                </div>
                
                <div className="mb-4">
                    <div className="text-5xl font-bold text-cyan-700">
                        {advTrends?.corrosion_index.value.toFixed(3)}
                    </div>
                </div>

                <div className="space-y-2 text-sm text-gray-600">
                    <div className="flex justify-between">
                        <span>Low Threshold:</span>
                        <span className="font-mono">{advTrends?.corrosion_index.threshold_low}</span>
                    </div>
                    <div className="flex justify-between">
                        <span>High Threshold:</span>
                        <span className="font-mono">{advTrends?.corrosion_index.threshold_high}</span>
                    </div>
                    <p className="mt-2 text-gray-500 italic">
                        Накопичувальний індекс, що залежить від вологості та часу. Впливає на ефективність охолодження (-{((advTrends?.modifiers.cooling_efficiency || 1) < 1 ? (1 - (advTrends?.modifiers.cooling_efficiency || 1))*100 : 0).toFixed(1)}%).
                    </p>
                </div>
            </div>

            {/* Fan Wear Index Card */}
            <div className="bg-white rounded-lg shadow p-6 border-l-4 border-gray-500">
                <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center">
                        <Fan className="w-6 h-6 mr-2 text-gray-600" />
                        <h2 className="text-xl font-bold">Індекс Зносу Вентиляторів (FWI)</h2>
                    </div>
                    <span className={`px-3 py-1 rounded-full text-sm font-bold ${
                        advTrends?.fan_wear_index.wear_level === 'critical' ? 'bg-red-100 text-red-700' :
                        advTrends?.fan_wear_index.wear_level === 'elevated' ? 'bg-yellow-100 text-yellow-700' :
                        'bg-blue-100 text-blue-700'
                    }`}>
                        {advTrends?.fan_wear_index.wear_level.toUpperCase()}
                    </span>
                </div>
                
                <div className="mb-4">
                    <div className="text-5xl font-bold text-gray-700">
                        {advTrends?.fan_wear_index.value.toFixed(1)}
                    </div>
                </div>

                <div className="space-y-2 text-sm text-gray-600">
                    <div className="flex justify-between">
                        <span>Elevated Threshold:</span>
                        <span className="font-mono">{advTrends?.fan_wear_index.threshold_elevated}</span>
                    </div>
                    <div className="flex justify-between">
                        <span>Critical Threshold:</span>
                        <span className="font-mono">{advTrends?.fan_wear_index.threshold_critical}</span>
                    </div>
                    <p className="mt-2 text-gray-500 italic">
                        Залежить від обертів (RPM), пилу та часу. Збільшує енергоспоживання (+{((advTrends?.modifiers.fan_power || 1) > 1 ? ((advTrends?.modifiers.fan_power || 1) - 1)*100 : 0).toFixed(1)}%).
                    </p>
                </div>
            </div>
        </div>

      </div>
    </div>
  );
}
