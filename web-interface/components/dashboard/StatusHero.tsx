'use client';
import { motion } from 'framer-motion';
import { Activity, Server, Clock, Power, ShieldCheck } from 'lucide-react';
import { SystemMode } from '@/lib/api';
import { cn } from '@/lib/utils';

interface Props {
  serverOnline: boolean;
  systemMode: SystemMode | null;
  lastUpdated: Date | null;
}

export function StatusHero({ serverOnline, systemMode, lastUpdated }: Props) {
  return (
    <motion.div 
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-white/80 backdrop-blur-md border border-white/20 shadow-xl rounded-2xl p-6 mb-8 w-full relative overflow-hidden"
    >
      <div className="absolute top-0 right-0 p-4 opacity-10 pointer-events-none">
        <Activity className="w-32 h-32" />
      </div>

      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6 relative z-10">
        <div className="flex items-center gap-4">
          <div className={cn(
            "p-3 rounded-xl shadow-lg transition-colors",
            serverOnline ? "bg-gradient-to-br from-green-400 to-green-600" : "bg-gradient-to-br from-red-400 to-red-600"
          )}>
            <Server className="w-8 h-8 text-white" />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-gray-800">
              {serverOnline ? "Система в нормі" : "З'єднання втрачено"}
            </h2>
            <p className={cn("text-sm font-medium", serverOnline ? "text-green-600" : "text-red-500")}>
              {serverOnline ? "Fog-сервер підключено • DB Connected" : "Fog-сервер недоступний"}
            </p>
          </div>
        </div>

        <div className="flex flex-col sm:flex-row gap-4 w-full md:w-auto">
          {/* Mode Badge */}
          <div className={cn(
            "flex items-center gap-3 px-5 py-3 rounded-xl border shadow-sm w-full md:w-auto transition-all",
            systemMode?.mode === 'auto' 
              ? "bg-blue-50/50 border-blue-200 text-blue-700 hover:bg-blue-50" 
              : "bg-purple-50/50 border-purple-200 text-purple-700 hover:bg-purple-50"
          )}>
            <ShieldCheck className="w-5 h-5" />
            <div className="flex flex-col">
              <span className="text-xs uppercase tracking-wider font-semibold opacity-70">Режим роботи</span>
              <span className="font-bold text-lg leading-tight">
                {systemMode?.mode === 'auto' ? "Автоматичний" : "Ручний"}
              </span>
            </div>
          </div>

          {/* Time Badge */}
          <div className="flex items-center gap-3 px-5 py-3 rounded-xl bg-gray-50/80 border border-gray-200 text-gray-600 shadow-sm w-full md:w-auto">
            <Clock className="w-5 h-5" />
            <div className="flex flex-col">
              <span className="text-xs uppercase tracking-wider font-semibold opacity-70">Останнє оновлення</span>
              <span className="font-mono font-medium text-lg leading-tight">
                {lastUpdated ? lastUpdated.toLocaleTimeString('uk-UA') : '--:--:--'}
              </span>
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
