/**
 * API-клиент для связи с fog-сервером
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';

export interface GPUTemp {
  gpu_id: number;
  temperature: number;
  load: number;
}
export type GpuTemperature = GPUTemp;

export interface Alert {
  gpu_id: number;
  temperature: number;
  threshold: number;
  severity: 'warning' | 'critical';
  timestamp: string;
  message?: string;
}

export interface CurrentState {
  gpu_temps: GPUTemp[];
  alerts: Alert[];
  timestamp: string;
}

export interface HistoryDataPoint {
  time: string;
  measurement: string;
  gpu_id?: string;
  value: number;
}

/**
 * Получает текущее состояние системы
 */
export async function getCurrentState(): Promise<CurrentState> {
  const response = await fetch(`${API_BASE_URL}/api/v1/current-state`);
  if (!response.ok) throw new Error('Failed to fetch current state');
  return response.json();
}

/**
 * Получает историю за последние N часов
 */
export async function getHistory(hours: number = 1): Promise<HistoryDataPoint[]> {
  const response = await fetch(`${API_BASE_URL}/api/v1/history?hours=${hours}`);
  if (!response.ok) throw new Error('Failed to fetch history');
  const json = await response.json();
  return json.data;
}

/**
 * Health check fog-сервера
 */
export async function healthCheck(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE_URL}/health`);
    return response.ok;
  } catch {
    return false;
  }
}

// ============================================================================
// НОВЫЕ ИНТЕРФЕЙСЫ
// ============================================================================

export interface FanStatistics {
  fan_id: number;
  avg_pwm_last_hour: number;
  max_pwm_last_hour: number;
  min_pwm_last_hour: number;
  time_on_high: number;
  current_rpm: number;
  current_pwm: number;
}

export interface SystemMode {
  mode: 'auto' | 'manual';
  last_changed: string;
  changed_by: string;
}

export interface ManualControlCommand {
  fan_id: number;
  pwm_duty: number;
}

export interface UserAction {
  timestamp: string;
  action: string;
  details: unknown;
}

// ============================================================================
// НОВЫЕ API ФУНКЦИИ
// ============================================================================

/**
 * Получает статистику работы вентиляторов
 */
export async function getFanStatistics(): Promise<FanStatistics[]> {
  const response = await fetch(`${API_BASE_URL}/api/v1/fan-statistics`);
  if (!response.ok) throw new Error('Failed to fetch fan statistics');
  const json = await response.json();
  return json.statistics;
}

/**
 * Получает текущий режим работы системы
 */
export async function getSystemMode(): Promise<SystemMode> {
  const response = await fetch(`${API_BASE_URL}/api/v1/system-mode`);
  if (!response.ok) throw new Error('Failed to fetch system mode');
  return response.json();
}

/**
 * Устанавливает режим работы системы
 */
export async function setSystemMode(mode: 'auto' | 'manual', deviceId: string = 'esp32_master_001'): Promise<unknown> {
  const response = await fetch(`${API_BASE_URL}/api/v1/system-mode`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mode, device_id: deviceId })
  });
  if (!response.ok) throw new Error('Failed to set system mode');
  return response.json() as Promise<unknown>;
}

/**
 * Устанавливает ручное управление вентиляторами
 */
export async function setManualFanControl(
  commands: ManualControlCommand[],
  deviceId: string = 'esp32_master_001'
): Promise<unknown> {
  const response = await fetch(`${API_BASE_URL}/api/v1/fan-control/manual`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      device_id: deviceId,
      mode: 'manual',
      commands
    })
  });
  if (!response.ok) {
    const errJson = (await response.json()) as Record<string, unknown>;
    const detail = typeof errJson['detail'] === 'string' ? errJson['detail'] : undefined;
    throw new Error(detail ?? 'Failed to set manual control');
  }
  return response.json() as Promise<unknown>;
}

/**
 * Получает историю действий пользователя
 */
export async function getUserActions(limit: number = 20): Promise<UserAction[]> {
  const response = await fetch(`${API_BASE_URL}/api/v1/user-actions?limit=${limit}`);
  if (!response.ok) throw new Error('Failed to fetch user actions');
  const json = await response.json() as { actions: UserAction[] };
  return json.actions;
}

export interface FanHistoryDataPoint {
  time: string;
  fan_id: string;
  field: 'pwm_duty' | 'rpm';
  value: number;
}

/**
 * Получает историю работы вентиляторов за последние N часов
 */
export async function getFanHistory(hours: number = 1): Promise<FanHistoryDataPoint[]> {
  const response = await fetch(`${API_BASE_URL}/api/v1/fan-history?hours=${hours}`);
  if (!response.ok) throw new Error('Failed to fetch fan history');
  const json = await response.json();
  return json.data;
}

// ============================================================================
// ENVIRONMENTAL MONITORING INTERFACES & API
// ============================================================================

export interface EnvironmentalSensorData {
  humidity: number;  // %
  dust: number;      // μg/m³
}

export interface EnvironmentalActuatorData {
  dehumidifier_active: boolean;
  dehumidifier_power: number;
  humidifier_active: boolean;
  humidifier_power: number;
}

export interface EnvironmentalAlert {
  alert_type: 'dust_high' | 'humidity_low' | 'humidity_high';
  current_value: number;
  threshold: number;
  severity: 'warning' | 'critical';
  timestamp: string;
  message: string;
}

export interface EnvironmentalState {
  humidity: number | null;
  dust: number | null;
  actuators: EnvironmentalActuatorData;
  alerts: EnvironmentalAlert[];
  timestamp: string;
}

export interface EnvironmentalHistoryPoint {
  time: string;
  field: 'humidity' | 'dust';
  value: number;
}

export interface EnvironmentalTrends {
  hourly_humidity_change_rate: {
    value: number | null;
    interpretation: string;
    formula: string;
  };
  hourly_dust_accumulation_rate: {
    value: number | null;
    interpretation: string;
    formula: string;
  };
  cooling_efficiency_modifier: {
    value: number;
    reduction_percent: number;
    formula: string;
  };
}


export interface AdvancedTrends {
  corrosion_index: {
    value: number;
    risk_level: 'low' | 'medium' | 'high';
    threshold_low: number;
    threshold_high: number;
  };
  fan_wear_index: {
    value: number;
    wear_level: 'normal' | 'elevated' | 'critical';
    threshold_elevated: number;
    threshold_critical: number;
  };
  modifiers: {
    cooling_efficiency: number;
    fan_power: number;
  };
}

export interface AdvancedTrendHistoryPoint {
  time: string;
  ci: number;
  ci_risk: string;
  fwi: number;
  fwi_wear: string;
}

export interface EnvironmentalControlCommand {
  dehumidifier_active: boolean;
  dehumidifier_power: number;
  humidifier_active: boolean;
  humidifier_power: number;
}

/**
 * Получает текущее состояние environmental параметров
 */
export async function getEnvironmentalState(): Promise<EnvironmentalState> {
  const response = await fetch(`${API_BASE_URL}/api/v1/environmental/current`);
  if (!response.ok) throw new Error('Failed to fetch environmental state');
  return response.json();
}

/**
 * Получает историю environmental параметров за последние N часов
 */
export async function getEnvironmentalHistory(hours: number = 1): Promise<EnvironmentalHistoryPoint[]> {
  const response = await fetch(`${API_BASE_URL}/api/v1/environmental/history?hours=${hours}`);
  if (!response.ok) throw new Error('Failed to fetch environmental history');
  const json = await response.json();
  return json.data;
}

/**
 * Получает вычисленные environmental тренды
 */
export async function getEnvironmentalTrends(): Promise<EnvironmentalTrends> {
  const response = await fetch(`${API_BASE_URL}/api/v1/environmental/trends`);
  if (!response.ok) throw new Error('Failed to fetch environmental trends');
  const json = await response.json();
  return json.trends;
}

/**
 * Устанавливает ручное управление environmental актуаторами
 */
export async function setEnvironmentalControl(command: EnvironmentalControlCommand): Promise<unknown> {
  const response = await fetch(`${API_BASE_URL}/api/v1/environmental/control`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(command)
  });
  if (!response.ok) throw new Error('Failed to set environmental control');
  return response.json();
}

/**
 * Получает продвинутые тренды (CI, FWI)
 */
export async function getAdvancedTrends(): Promise<AdvancedTrends> {
  const response = await fetch(`${API_BASE_URL}/api/v1/trends/advanced`);
  if (!response.ok) throw new Error('Failed to fetch advanced trends');
  return response.json();
}

/**
 * Получает историю продвинутых трендов
 */
export async function getAdvancedTrendsHistory(hours: number = 24): Promise<AdvancedTrendHistoryPoint[]> {
  const response = await fetch(`${API_BASE_URL}/api/v1/trends/advanced/history?hours=${hours}`);
  if (!response.ok) throw new Error('Failed to fetch advanced trends history');
  const json = await response.json();
  return json.data;
}

/**
 * Сбрасывает продвинутые тренды в 0
 */
export async function resetAdvancedTrends(): Promise<unknown> {
  const response = await fetch(`${API_BASE_URL}/api/v1/trends/advanced/reset`, {
    method: 'POST'
  });
  if (!response.ok) throw new Error('Failed to reset trends');
  return response.json();
}

/**
 * Устанавливает системный профиль оточення (admin)
 */
export async function setSystemProfile(profileId: number): Promise<unknown> {
  const response = await fetch(`${API_BASE_URL}/api/v1/admin/profile`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ profile_id: profileId })
  });
  if (!response.ok) throw new Error('Failed to set profile');
  return response.json();
}

/**
 * Получает текущий target profile
 */
export async function getSystemProfile(): Promise<{profile_id: number}> {
    const response = await fetch(`${API_BASE_URL}/api/v1/system/profile`);
    if (!response.ok) throw new Error('Failed to get profile');
    return response.json();
}
