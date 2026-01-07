# AI Coding Agent Instructions for GPU Cluster Cooling System

## Architecture Overview
This is a fog computing system for real-time monitoring and adaptive cooling control of GPU clusters. It consists of three main components:

- **Hardware Emulator** (`hardware-emulator/`): Simulates ESP32 hardware, GPU temperatures, fan controllers, and room environment
- **Fog Server** (`fog-server/`): FastAPI backend that receives telemetry, stores data in InfluxDB, runs cascade cooling algorithms, and provides REST API
- **Web Interface** (`web-interface/`): Next.js dashboard with real-time polling for monitoring and manual control

Data flows: Hardware → Fog Server → InfluxDB, with Web Interface polling Fog Server every 5 seconds.

## Key Patterns & Conventions

### Configuration Management
- **Fog Server**: Environment variables via `.env` file (see `fog-server/.env`)
- **Hardware Emulator**: YAML config (`hardware-emulator/config.yaml`) for simulation parameters
- **Web Interface**: `NEXT_PUBLIC_API_URL` for Fog Server endpoint

### API Design
- RESTful endpoints under `/api/v1/` (e.g., `/api/v1/current-state`, `/api/v1/telemetry`)
- Pydantic models for request/response validation (see `fog-server/app/main.py` models)
- CORS enabled for cross-origin requests from web interface

### Cooling Algorithm
Cascade control in `CoolingAlgorithm` class:
1. Base PWM calculated from GPU temperature (20-100% range)
2. Room temperature correction (±30% influence)
3. PWM smoothing to prevent fan oscillations (>10% changes applied gradually)

### Real-Time Updates
- Web interface polls Fog Server every 5 seconds using `Promise.all()` for parallel API calls
- Hardware sends telemetry every 30 seconds via HTTP POST
- Use React `useEffect` with `setInterval` for polling (see `web-interface/app/page.tsx`)

### Data Storage
- InfluxDB for time-series data with measurements, fields, and tags
- Retention policies for automatic data cleanup
- Flux queries for historical data aggregation

### Development Workflow
1. Start InfluxDB locally
2. Run `python hardware-emulator/main.py` to simulate hardware
3. Run `uvicorn fog-server.app.main:app --reload` for backend
4. Run `npm run dev` in `web-interface/` for frontend
5. Access dashboard at `http://localhost:3000`

### Error Handling
- Health checks via `/health` endpoint
- Alert system for temperature thresholds (warning: 90°C, critical: 120°C)
- Graceful degradation when Fog Server is offline

### File Structure Conventions
- `app/` directories for main application code
- `lib/` for shared utilities (e.g., API client in `web-interface/lib/api.ts`)
- `components/` for reusable UI components
- Configuration files at project roots

When adding features, maintain the fog computing architecture: keep processing close to data sources, use polling for real-time updates, and ensure all components can run independently for testing.