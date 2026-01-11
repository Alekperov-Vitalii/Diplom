'use client';

import { useEffect, useState } from 'react';
import { getEnvironmentalTrends, EnvironmentalTrends } from '@/lib/api';
import { TrendingUp, Wind, Gauge, ArrowLeft } from 'lucide-react';
import Link from 'next/link';

export default function TrendsPage() {
  const [trends, setTrends] = useState<EnvironmentalTrends | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchTrends = async () => {
      try {
        const data = await getEnvironmentalTrends();
        setTrends(data);
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
      </div>
    </div>
  );
}
