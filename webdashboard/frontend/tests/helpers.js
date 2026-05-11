import { expect } from '@playwright/test'

// ── Shared mock data ──────────────────────────────────────────────────────────

export const CONNECTED_STATE = {
  connected: true,
  ip: '192.168.1.100',
  device_id: 'TESTFAN000000001',
  power: true,
  speed: 1,
  manual_speed: 128,
  operation_mode: 0,
  operation_mode_name: 'Ventilation',
  boost_active: false,
  humidity_sensor: 0,
  humidity_threshold: 60,
  current_humidity: 45,
  fan1_rpm: 1200,
  fan2_rpm: 1150,
  alarm_status: 0,
  alarm_name: '',
  weekly_schedule_enabled: false,
  rtc_time: '10:30:00',
  rtc_calendar: '2026-05-11',
}

export const SCENARIOS = [
  {
    name: 'Night',
    fans: [{ device_id: 'TESTFAN000000001', settings: { power: true, speed: 1, manual_speed: null, operation_mode: null, boost_active: null, humidity_sensor: null, humidity_threshold: null } }],
  },
  {
    name: 'Boost',
    fans: [{ device_id: 'TESTFAN000000001', settings: { power: true, speed: null, manual_speed: null, operation_mode: null, boost_active: true, humidity_sensor: null, humidity_threshold: null } }],
  },
]

export const QUICK_SLOTS = {
  device_id: 'TESTFAN000000001',
  slots: ['Night', null, null],
}

export const DISCOVERED = [
  { ip: '192.168.1.100', device_id: 'TESTFAN000000001', unit_type: 3, unit_type_name: 'Vento Expert' },
]

export const SCHEDULE = {
  periods: Array.from({ length: 8 }, (_row, _day) =>
    Array.from({ length: 4 }, (_col, p) => ({ speed: (p % 3) + 1, end_h: (p + 1) * 6, end_m: 0 }))
  ),
}

// ── Route mocking ─────────────────────────────────────────────────────────────

/**
 * Register a single catch-all handler for all /api/** requests.
 * Pass overrides as { 'METHOD /path': route => ... } to override specific routes.
 * Dynamic paths (with device names/IDs) are matched by prefix or suffix.
 */
export async function setupApiRoutes(page, overrides = {}) {
  await page.route('**/api/**', route => {
    const url = route.request().url()
    const method = route.request().method()
    const path = new URL(url).pathname

    const key = `${method} ${path}`
    if (key in overrides) return overrides[key](route)

    if (method === 'GET'    && path === '/api/state')                         return route.fulfill({ json: CONNECTED_STATE })
    if (method === 'GET'    && path === '/api/scenarios')                     return route.fulfill({ json: SCENARIOS })
    if (method === 'POST'   && path === '/api/scenarios')                     return route.fulfill({ json: SCENARIOS[0] })
    if (method === 'GET'    && path.startsWith('/api/scenarios/quick-slots/')) return route.fulfill({ json: QUICK_SLOTS })
    if (method === 'PUT'    && path.startsWith('/api/scenarios/quick-slots/')) return route.fulfill({ json: QUICK_SLOTS })
    if (method === 'POST'   && path.endsWith('/apply'))                        return route.fulfill({ status: 204, body: '' })
    if (method === 'POST'   && path.endsWith('/add-fan'))                      return route.fulfill({ status: 204, body: '' })
    if (method === 'DELETE' && path.startsWith('/api/scenarios/'))             return route.fulfill({ status: 204, body: '' })
    if (method === 'GET'    && path === '/api/devices')                        return route.fulfill({ json: DISCOVERED })
    if (method === 'POST'   && path === '/api/connect')                        return route.fulfill({ json: CONNECTED_STATE })
    if (method === 'DELETE' && path === '/api/connect')                        return route.fulfill({ status: 204, body: '' })
    if (method === 'GET'    && path === '/api/command/schedule')                return route.fulfill({ json: SCHEDULE })
    if (path.startsWith('/api/command/'))                                      return route.fulfill({ status: 204, body: '' })

    route.continue()
  })
}

/** Intercept the WebSocket so tests work without a live backend. */
export async function mockWebSocket(page) {
  await page.routeWebSocket('**/ws', _ws => {
    // Connection accepted silently — state is driven by HTTP mocks only
  })
}

// ── Navigation helpers ────────────────────────────────────────────────────────

/** Navigate to the app and wait until the dashboard shows "Connected". */
export async function gotoConnected(page) {
  await setupApiRoutes(page)
  await mockWebSocket(page)
  await page.goto('/')
  await expect(page.locator('.status-label')).toHaveText('Connected')
}

/** Navigate to the app and wait until the connect dialog is shown. */
export async function gotoDisconnected(page) {
  await setupApiRoutes(page, {
    'GET /api/state': route => route.fulfill({ status: 503, json: { detail: 'Not connected' } }),
  })
  await mockWebSocket(page)
  await page.goto('/')
  await expect(page.locator('[role="dialog"][aria-label="Connect to device"]')).toBeVisible()
}

/** Open the Fan Details modal (assumes app is in connected state). */
export async function openDetails(page) {
  await page.getByRole('button', { name: 'Details…' }).click()
  await expect(page.locator('[role="dialog"][aria-label="Fan details"]')).toBeVisible()
}
