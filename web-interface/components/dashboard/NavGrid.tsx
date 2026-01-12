'use client';
import { motion } from 'framer-motion';
import Link from 'next/link';
import { History, TrendingUp, Sliders, Shield, ArrowRight } from 'lucide-react';
import { cn } from '@/lib/utils';

const links = [
  { 
    href: '/history', 
    label: 'Історія', 
    sub: 'Графіки та аналіз', 
    icon: History, 
    color: 'bg-blue-500', 
    gradient: 'from-blue-500 to-blue-600',
    shadow: 'shadow-blue-200'
  },
  { 
    href: '/trends', 
    label: 'Тренди', 
    sub: 'Ефективність системи', 
    icon: TrendingUp, 
    color: 'bg-purple-500', 
    gradient: 'from-purple-500 to-purple-600',
    shadow: 'shadow-purple-200'
  },
  { 
    href: '/control', 
    label: 'Керування', 
    sub: 'Вентилятори та клімат', 
    icon: Sliders, 
    color: 'bg-green-500', 
    gradient: 'from-green-500 to-green-600',
    shadow: 'shadow-green-200'
  },
  { 
    href: '/admin', 
    label: 'Адмін', 
    sub: 'Налаштування профілів', 
    icon: Shield, 
    color: 'bg-orange-500', 
    gradient: 'from-orange-500 to-orange-600',
    shadow: 'shadow-orange-200'
  }
];

export function NavGrid() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
      {links.map((link, idx) => {
        const Icon = link.icon;
        return (
          <Link key={link.href} href={link.href} className="block group">
            <motion.div
              whileHover={{ y: -5, scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: idx * 0.1 }}
              className={cn(
                "relative bg-white rounded-2xl p-6 shadow-lg border border-gray-100 overflow-hidden text-left h-full flex flex-col justify-between",
                `hover:${link.shadow} hover:shadow-xl transition-all duration-300`
              )}
            >
              <div className={cn(
                "absolute top-0 right-0 w-24 h-24 rounded-bl-full opacity-10 transition-transform group-hover:scale-110", 
                link.color
              )} />
              
              <div className="mb-4">
                <div className={cn(
                  "w-12 h-12 rounded-xl flex items-center justify-center text-white shadow-md mb-4 bg-linear-to-br",
                  link.gradient
                )}>
                  <Icon className="w-6 h-6" />
                </div>
                <h3 className="text-xl font-bold text-gray-800 leading-tight group-hover:text-gray-900">
                  {link.label}
                </h3>
                <p className="text-sm text-gray-500 mt-1 font-medium">
                  {link.sub}
                </p>
              </div>

              <div className="flex items-center text-sm font-semibold text-gray-400 group-hover:text-gray-800 transition-colors mt-auto">
                <span className="mr-2">Перейти</span>
                <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
              </div>
            </motion.div>
          </Link>
        );
      })}
    </div>
  );
}
