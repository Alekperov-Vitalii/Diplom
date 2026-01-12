'use client';
import { motion } from 'framer-motion';
import { Droplets, Cloud, Zap } from 'lucide-react';
import { EnvironmentalState } from '@/lib/api';
import { cn } from '@/lib/utils';

interface Props {
  envState: EnvironmentalState | null;
}

export function ClimateWidget({ envState }: Props) {
  if (!envState) return null;

  const { humidity, dust, actuators } = envState;
  
  // Humidity Status
  const humVal = humidity ?? 0;
  const isHumOptimal = humVal >= 40 && humVal <= 60;
  const isHumLow = humVal < 40;
  
  // Dust Status
  const dustVal = dust ?? 0;
  const isDustLow = dustVal < 25;
  const isDustMod = dustVal >= 25 && dustVal < 50;

  return (
    <motion.div 
       initial={{ opacity: 0, scale: 0.95 }}
       animate={{ opacity: 1, scale: 1 }}
       className="bg-white rounded-2xl shadow-xl border border-gray-100 p-6 mb-8 overflow-hidden relative"
    >
      <div className="flex items-center gap-3 mb-6 relative z-10">
         <div className="bg-blue-100 p-2 rounded-lg text-blue-600">
            <Droplets className="w-6 h-6" />
         </div>
         <h2 className="text-2xl font-bold text-gray-800">Клімат-контроль</h2>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 relative z-10">
        
        {/* Humidity Block */}
        <div className={cn(
            "p-5 rounded-xl border relative transition-all group", 
            isHumOptimal ? "bg-green-50/50 border-green-200" : isHumLow ? "bg-blue-50/50 border-blue-200" : "bg-red-50/50 border-red-200"
        )}>
           <div className="flex justify-between items-start mb-2">
              <span className="text-sm font-semibold uppercase tracking-wider text-gray-500">Вологість</span>
              <Droplets className={cn("w-5 h-5", isHumOptimal ? "text-green-500" : isHumLow ? "text-blue-500" : "text-red-500")} />
           </div>
           <div className="flex items-baseline gap-2">
              <span className="text-4xl font-bold text-gray-900">{humVal.toFixed(1)}</span>
              <span className="text-lg text-gray-500">%</span>
           </div>
           <div className="mt-3 flex items-center gap-2">
              <div className={cn("px-2 py-1 rounded text-xs font-bold uppercase", 
                  isHumOptimal ? "bg-green-100 text-green-700" : isHumLow ? "bg-blue-100 text-blue-700" : "bg-red-100 text-red-700")}>
                  {isHumOptimal ? "Оптимально" : isHumLow ? "Низька" : "Висока"}
              </div>
              {/* Active Device Indicator */}
              {actuators.humidifier_active && (
                 <div className="flex items-center gap-1 text-xs font-semibold text-blue-600 animate-pulse">
                    <Zap className="w-3 h-3" />
                    Зволожувач {actuators.humidifier_power}%
                 </div>
              )}
              {actuators.dehumidifier_active && (
                 <div className="flex items-center gap-1 text-xs font-semibold text-orange-600 animate-pulse">
                    <Zap className="w-3 h-3" />
                    Осушувач {actuators.dehumidifier_power}%
                 </div>
              )}
           </div>
        </div>

        {/* Dust Block */}
        <div className={cn(
            "p-5 rounded-xl border relative transition-all group", 
            isDustLow ? "bg-emerald-50/50 border-emerald-200" : isDustMod ? "bg-yellow-50/50 border-yellow-200" : "bg-red-50/50 border-red-200"
        )}>
           <div className="flex justify-between items-start mb-2">
              <span className="text-sm font-semibold uppercase tracking-wider text-gray-500">Якість повітря (Пил)</span>
              <Cloud className={cn("w-5 h-5", isDustLow ? "text-emerald-500" : isDustMod ? "text-yellow-500" : "text-red-500")} />
           </div>
           <div className="flex items-baseline gap-2">
              <span className="text-4xl font-bold text-gray-900">{dustVal.toFixed(1)}</span>
              <span className="text-lg text-gray-500">μg/m³</span>
           </div>
           <div className="mt-3 flex items-center gap-2">
              <div className={cn("px-2 py-1 rounded text-xs font-bold uppercase", 
                  isDustLow ? "bg-emerald-100 text-emerald-700" : isDustMod ? "bg-yellow-100 text-yellow-700" : "bg-red-100 text-red-700")}>
                  {isDustLow ? "Чисто" : isDustMod ? "Помірно" : "Брудно"}
              </div>
              {/* Active Device Placeholder for Dust (If Fan were used for purge?) */}
              {/* Example: If Fans > 80% PWM maybe show "Purge"? Not implemented yet but structure allows it. */}
           </div>
        </div>

      </div>

      {/* Background Decor */}
      <div className="absolute -bottom-10 -right-10 w-40 h-40 bg-blue-500/5 rounded-full blur-3xl" />
      <div className="absolute -top-10 -left-10 w-40 h-40 bg-green-500/5 rounded-full blur-3xl" />
    </motion.div>
  );
}
