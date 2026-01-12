'use client';
import { motion } from 'framer-motion';
import { Thermometer, Cpu } from 'lucide-react';
import { GpuTemperature } from '@/lib/api';
import { cn } from '@/lib/utils';

interface Props {
  gpuTemps: GpuTemperature[];
}

export function GpuGrid({ gpuTemps }: Props) {
  return (
    <div className="mb-8">
      <div className="flex items-center gap-3 mb-6">
         <div className="bg-red-100 p-2 rounded-lg text-red-600">
            <Thermometer className="w-6 h-6" />
         </div>
         <h2 className="text-2xl font-bold text-gray-800">Моніторинг GPU</h2>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {gpuTemps.sort((a,b) => a.gpu_id - b.gpu_id).map((gpu, idx) => {
           const temp = gpu.temperature;
           const load = gpu.load || 0;
           const isHot = temp >= 90;
           const isWarm = temp >= 70;
           
           return (
             <motion.div
               key={gpu.gpu_id}
               initial={{ opacity: 0, y: 20 }}
               animate={{ opacity: 1, y: 0 }}
               transition={{ delay: idx * 0.05 }}
               className="bg-white rounded-xl shadow-lg border border-gray-100 p-5 hover:shadow-xl transition-shadow relative overflow-hidden"
             >
                {/* Status Color Bar */}
                <div className={cn(
                   "absolute top-0 left-0 w-full h-1",
                   isHot ? "bg-red-500" : isWarm ? "bg-yellow-500" : "bg-green-500"
                )} />

                <div className="flex justify-between items-start mb-4">
                   <div className="flex items-center gap-2">
                      <Cpu className="w-5 h-5 text-gray-400" />
                      <span className="font-bold text-gray-700">GPU {gpu.gpu_id}</span>
                   </div>
                   <span className={cn(
                      "text-sm font-bold px-2 py-0.5 rounded",
                      isHot ? "bg-red-100 text-red-700" : isWarm ? "bg-yellow-100 text-yellow-700" : "bg-green-100 text-green-700"
                   )}>
                      {isHot ? 'CRITICAL' : isWarm ? 'WARN' : 'OK'}
                   </span>
                </div>

                <div className="flex items-end gap-2 mb-6">
                   <span className="text-4xl font-extrabold text-gray-900">{temp.toFixed(1)}</span>
                   <span className="text-lg text-gray-500 mb-1">°C</span>
                </div>

                {/* Load Bar */}
                <div>
                   <div className="flex justify-between text-xs text-gray-500 mb-1 font-semibold uppercase tracking-wider">
                      <span>Навантаження</span>
                      <span>{load.toFixed(0)}%</span>
                   </div>
                   <div className="w-full bg-gray-100 rounded-full h-2 overflow-hidden">
                      <motion.div 
                        initial={{ width: 0 }}
                        animate={{ width: `${load}%` }}
                        transition={{ duration: 1, ease: "easeOut" }}
                        className={cn(
                           "h-full rounded-full",
                           load > 90 ? "bg-red-500" : load > 60 ? "bg-blue-500" : "bg-green-500"
                        )}
                      />
                   </div>
                </div>
             </motion.div>
           );
        })}
      </div>
    </div>
  );
}
