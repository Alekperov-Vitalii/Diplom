/**
 * API-клиент для связи с fog-сервером
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';

export interface GPUTemp {
  gpu_id: number;
  temperature: number;
  load: number;
}

export interface Alert {
  gpu_id: number;
  temperature: number;
  threshold: number;
  severity: 'warning' | 'critical';
  timestamp: string;
}

export interface CurrentState {
  gpu_temps: GPUTemperature[];
  alerts: Alert[];
  environment?: EnvironmentState;
  timestamp: string;
}

export interface EnvironmentState {
  humidity: number;
  dust_level: number;
  humidifier: boolean;
  dehumidifier: boolean;
  air_purifier: boolean;
}

export interface GPUTemperature {
  gpu_id: number;
  temperature: number;
  load: number;
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