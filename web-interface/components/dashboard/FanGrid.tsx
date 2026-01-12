'use client';
import { motion } from 'framer-motion';
import { Fan, RefreshCw, Zap } from 'lucide-react';
import { FanStatistics, SystemMode } from '@/lib/api';
import { cn } from '@/lib/utils';

interface Props {
  fanStats: FanStatistics[];
  systemMode: SystemMode | null;
}

export function FanGrid({ fanStats, systemMode }: Props) {
  return (
    <div className="mb-8">
      <div className="flex items-center gap-3 mb-6">
         <div className="bg-purple-100 p-2 rounded-lg text-purple-600">
            <Fan className="w-6 h-6 animate-spin-slow" />
         </div>
         <h2 className="text-2xl font-bold text-gray-800">Система охолодження</h2>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {fanStats.map((fan, idx) => {
           const pwm = fan.current_pwm || 0;
           const rpm = fan.current_rpm || 0;
           const isMax = pwm >= 99;
           
           return (
             <motion.div
               key={fan.fan_id}
               initial={{ opacity: 0, y: 20 }}
               animate={{ opacity: 1, y: 0 }}
               transition={{ delay: 0.2 + (idx * 0.05) }}
               className="bg-white rounded-xl shadow-lg border border-gray-100 p-5 hover:shadow-xl transition-shadow relative overflow-hidden group"
             >
                <div className="flex justify-between items-center mb-4">
                   <div className="flex items-center gap-2">
                      <div className={cn("p-2 rounded-lg transition-colors", isMax ? "bg-purple-100 text-purple-600" : "bg-gray-100 text-gray-500")}>
                         <Fan className={cn("w-5 h-5", rpm > 0 && "animate-spin")} style={{ animationDuration: `${60000 / (rpm || 1)}ms` }} />
                      </div>
                      <span className="font-bold text-gray-700">Вентилятор {fan.fan_id}</span>
                   </div>
                   <div className="text-xs font-bold text-gray-400 bg-gray-50 px-2 py-1 rounded border">
                      #{fan.fan_id}
                   </div>
                </div>

                <div className="grid grid-cols-2 gap-4 mb-4">
                   <div className="bg-gray-50 rounded-lg p-3 text-center">
                      <div className="text-xs text-gray-500 uppercase font-bold tracking-wider mb-1">PWM</div>
                      <div className="text-xl font-bold text-purple-600">{pwm.toFixed(0)}%</div>
                   </div>
                   <div className="bg-gray-50 rounded-lg p-3 text-center">
                      <div className="text-xs text-gray-500 uppercase font-bold tracking-wider mb-1">RPM</div>
                      <div className="text-xl font-bold text-gray-700">{rpm.toFixed(0)}</div>
                   </div>
                </div>

                {/* Status text */}
                <div className="flex items-center justify-center gap-1 text-xs text-gray-400 font-medium">
                   {systemMode?.mode === 'auto' ? (
                      <>
                        <RefreshCw className="w-3 h-3" />
                        <span>Авто-керування</span>
                      </>
                   ) : (
                      <>
                        <Zap className="w-3 h-3" />
                        <span>Ручне керування</span>
                      </>
                   )}
                </div>
             </motion.div>
           );
        })}
      </div>
    </div>
  );
}
