'use client';
import { motion, AnimatePresence } from 'framer-motion';
import { AlertTriangle } from 'lucide-react';
import { Alert } from '@/lib/api';
import { cn } from '@/lib/utils';

interface Props {
  alerts: Alert[];
}

export function AlertsSystem({ alerts }: Props) {
  // Use local state to allow dismissing? 
  // For now, sink with props. But maybe auto-dismiss is handled by backend.
  // We just display what is active.
  
  if (!alerts || alerts.length === 0) return null;

  return (
    <div className="fixed bottom-6 right-6 z-50 flex flex-col gap-3 max-w-md w-full pointer-events-none">
       <AnimatePresence>
         {alerts.map((alert, idx) => (
            <motion.div
               key={`${alert.gpu_id}-${idx}`}
               initial={{ opacity: 0, x: 50, scale: 0.9 }}
               animate={{ opacity: 1, x: 0, scale: 1 }}
               exit={{ opacity: 0, scale: 0.9, transition: { duration: 0.2 } }}
               className={cn(
                 "pointer-events-auto p-4 rounded-xl shadow-2xl border-l-4 flex items-start gap-3 backdrop-blur-md",
                 alert.severity === 'critical' 
                   ? "bg-red-50/95 border-red-500 text-red-900 shadow-red-500/20" 
                   : "bg-yellow-50/95 border-yellow-500 text-yellow-900 shadow-yellow-500/20"
               )}
            >
               <div className={cn("p-2 rounded-full shrink-0", alert.severity === 'critical' ? "bg-red-100 text-red-600" : "bg-yellow-100 text-yellow-600")}>
                  <AlertTriangle className="w-5 h-5" />
               </div>
               <div className="flex-1">
                  <h4 className="font-bold text-sm uppercase tracking-wide mb-1">
                     {alert.severity === 'critical' ? 'Критична помилка' : 'Попередження'}
                  </h4>
                  <p className="text-sm font-medium leading-relaxed">
                     GPU {alert.gpu_id}: {alert.message || `${alert.temperature.toFixed(1)}°C (Поріг ${alert.threshold}°C)`}
                  </p>
               </div>
            </motion.div>
         ))}
       </AnimatePresence>
    </div>
  );
}
