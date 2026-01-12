"use client"

import React, { useState, useEffect } from 'react';
import { setSystemProfile, resetAdvancedTrends, getSystemProfile } from '@/lib/api';
import { 
    Factory, 
    CloudRain, 
    Sun, 
    Server, 
    RefreshCw, 
    CheckCircle, 
    AlertTriangle, 
    Home,
    ArrowLeft,
    Trash2
} from 'lucide-react';
import Link from 'next/link';

// Profiles definition
const PROFILES = [
  { 
    id: 1, 
    name: 'Офісне приміщення', 
    description: 'Стандартні умови. Комфортна вологість, мінімальна запиленість.',
    icon: Home,
    color: 'bg-blue-50 border-blue-200 text-blue-800 hover:bg-blue-100',
    activeColor: 'ring-2 ring-blue-500 bg-blue-100',
    humidity: '40-60%',
    dust: 'Low'
  },
  { 
    id: 5, 
    name: 'Дата-центр (Clean Room)', 
    description: 'Оптимальні умови. Строгий контроль клімату та фільтрації.',
    icon: Server,
    color: 'bg-indigo-50 border-indigo-200 text-indigo-800 hover:bg-indigo-100',
    activeColor: 'ring-2 ring-indigo-500 bg-indigo-100',
    humidity: '45-50%',
    dust: 'Very Low'
  },
  { 
    id: 8, 
    name: 'Промисловий цех', 
    description: 'Важкі умови. Висока запиленість, можливі перепади температур.',
    icon: Factory,
    color: 'bg-orange-50 border-orange-200 text-orange-800 hover:bg-orange-100',
    activeColor: 'ring-2 ring-orange-500 bg-orange-100',
    humidity: '30-80%',
    dust: 'High'
  },
  { 
    id: 3, 
    name: 'Прибережна зона', 
    description: 'Висока вологість, солоне повітря. Високий ризик корозії.',
    icon: CloudRain,
    color: 'bg-cyan-50 border-cyan-200 text-cyan-800 hover:bg-cyan-100',
    activeColor: 'ring-2 ring-cyan-500 bg-cyan-100',
    humidity: '70-90%',
    dust: 'Low'
  },
  { 
    id: 9, 
    name: 'Пустеля', 
    description: 'Екстремально сухо і гаряче. Дуже висока запиленість (пісок).',
    icon: Sun,
    color: 'bg-yellow-50 border-yellow-200 text-yellow-800 hover:bg-yellow-100',
    activeColor: 'ring-2 ring-yellow-500 bg-yellow-100',
    humidity: '10-20%',
    dust: 'Very High'
  }
];

export default function AdminPage() {
    const [currentProfileId, setCurrentProfileId] = useState<number | null>(null);
    const [loading, setLoading] = useState(false);
    const [message, setMessage] = useState<{type: 'success' | 'error', text: string} | null>(null);

    useEffect(() => {
        loadCurrentProfile();
    }, []);

    const loadCurrentProfile = async () => {
        try {
            const data = await getSystemProfile();
            setCurrentProfileId(data.profile_id);
        } catch (e) {
            console.error("Failed to load profile", e);
        }
    };

    const handleProfileSelect = async (id: number) => {
        if (loading || currentProfileId === id) return;
        
        setLoading(true);
        setMessage(null);
        try {
            await setSystemProfile(id);
            setCurrentProfileId(id);
            setMessage({ type: 'success', text: `Профіль змінено! Тренди CI/FWI скинуто.` });
            
            // Auto hide message
            setTimeout(() => setMessage(null), 5000);
        } catch (e) {
            setMessage({ type: 'error', text: 'Помилка зміни профілю' });
        } finally {
            setLoading(false);
        }
    };

    const handleResetTrends = async () => {
        if (loading) return;
        
        setLoading(true);
        try {
            await resetAdvancedTrends();
            setMessage({ type: 'success', text: 'Тренди успішно скинуто в 0!' });
            setTimeout(() => setMessage(null), 3000);
        } catch (e) {
            setMessage({ type: 'error', text: 'Помилка скидання трендів' });
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen bg-gray-50 p-6">
            <div className="max-w-7xl mx-auto space-y-6">
                {/* Header */}
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <Link href="/" className="p-2 hover:bg-gray-200 rounded-full transition-colors">
                            <ArrowLeft className="w-6 h-6 text-gray-600" />
                        </Link>
                        <div>
                            <h1 className="text-2xl font-bold text-gray-900">Адміністративна Панель</h1>
                            <p className="text-gray-500">Керування профілями емуляції та скидання метрик</p>
                        </div>
                    </div>
                </div>

                {/* Notifications */}
                {message && (
                    <div className={`p-4 rounded-lg flex items-center gap-3 ${
                        message.type === 'success' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                    } animate-in fade-in slide-in-from-top-4 duration-300`}>
                        {message.type === 'success' ? <CheckCircle className="w-5 h-5" /> : <AlertTriangle className="w-5 h-5" />}
                        <span className="font-medium">{message.text}</span>
                    </div>
                )}

                {/* Profiles Section */}
                <section className="space-y-4">
                    <h2 className="text-xl font-semibold text-gray-800 flex items-center gap-2">
                        <Server className="w-5 h-5" />
                        Вибір Профілю Оточення
                    </h2>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {PROFILES.map((profile) => {
                            const Icon = profile.icon;
                            const isActive = currentProfileId === profile.id;
                            
                            return (
                                <div 
                                    key={profile.id}
                                    onClick={() => handleProfileSelect(profile.id)}
                                    className={`
                                        relative group cursor-pointer p-6 rounded-xl border transition-all duration-300
                                        ${isActive ? profile.activeColor + ' shadow-md scale-[1.02]' : 'bg-white border-gray-200 hover:shadow-lg hover:-translate-y-1'}
                                        ${loading ? 'opacity-50 pointer-events-none' : ''}
                                    `}
                                >
                                    <div className="flex items-start justify-between mb-4">
                                        <div className={`p-3 rounded-lg ${profile.color.split(' ')[0]}`}>
                                            <Icon className={`w-8 h-8 ${profile.color.split(' ').pop()}`} />
                                        </div>
                                        {isActive && (
                                            <div className="bg-green-500 text-white text-xs font-bold px-2 py-1 rounded-full flex items-center gap-1">
                                                <CheckCircle className="w-3 h-3" />
                                                ACTIVE
                                            </div>
                                        )}
                                    </div>
                                    
                                    <h3 className="text-lg font-bold text-gray-900 mb-2">{profile.name}</h3>
                                    <p className="text-sm text-gray-500 mb-4 h-10">{profile.description}</p>
                                    
                                    <div className="flex items-center gap-3 text-sm font-medium text-gray-600 bg-gray-50 p-2 rounded-lg">
                                        <span className="flex items-center gap-1">
                                            <CloudRain className="w-4 h-4 text-blue-500" />
                                            {profile.humidity}
                                        </span>
                                        <span className="w-px h-4 bg-gray-300"></span>
                                        <span className="flex items-center gap-1">
                                            <Sun className="w-4 h-4 text-orange-500" />
                                            Dust: {profile.dust}
                                        </span>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </section>

                {/* Advanced Controls Section */}
                <section className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
                    <h2 className="text-xl font-semibold text-gray-800 flex items-center gap-2">
                        <RefreshCw className="w-5 h-5" />
                        Керування Трендами
                    </h2>
                    <div className="flex items-center justify-between">
                        <div className="max-w-2xl">
                            <h3 className="font-medium text-gray-900">Скидання індексів зносу (CI & FWI)</h3>
                            <p className="text-sm text-gray-500 mt-1">
                                Використовуйте цю функцію, якщо ви замінили обладнання або провели технічне обслуговування. 
                                Це обнулить накопичені значення корозії та зносу вентиляторів.
                            </p>
                        </div>
                        <button
                            onClick={handleResetTrends}
                            disabled={loading}
                            className={`
                                flex items-center gap-2 px-6 py-3 rounded-lg font-medium transition-all
                                bg-red-50 text-red-600 hover:bg-red-100 border border-red-200
                                ${loading ? 'opacity-50 cursor-not-allowed' : ''}
                            `}
                        >
                            <Trash2 className="w-5 h-5" />
                            Скинути Тренди
                        </button>
                    </div>
                </section>
            </div>
        </div>
    );
}
