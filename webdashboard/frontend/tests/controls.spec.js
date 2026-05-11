import { test, expect } from '@playwright/test'
import { gotoConnected, setupApiRoutes, mockWebSocket, CONNECTED_STATE } from './helpers.js'

test.describe('Device controls', () => {
  test.beforeEach(async ({ page }) => {
    await gotoConnected(page)
  })

  // ── Power ───────────────────────────────────────────────────────────────────

  test('power button shows ON when device is powered on', async ({ page }) => {
    await expect(page.locator('.power-label')).toHaveText('ON')
    await expect(page.locator('.power-btn')).toHaveAttribute('aria-pressed', 'true')
  })

  test('power button shows OFF when device is powered off', async ({ page }) => {
    await setupApiRoutes(page, {
      'GET /api/state': route => route.fulfill({ json: { ...CONNECTED_STATE, power: false } }),
    })
    await mockWebSocket(page)
    await page.goto('/')
    await expect(page.locator('.status-label')).toHaveText('Connected')
    await expect(page.locator('.power-label')).toHaveText('OFF')
    await expect(page.locator('.power-btn')).toHaveAttribute('aria-pressed', 'false')
  })

  test('clicking power button sends setPower request with toggled value', async ({ page }) => {
    let body = null
    await page.route('**/api/command/power', async route => {
      body = await route.request().postDataJSON()
      route.fulfill({ status: 204, body: '' })
    })

    await page.locator('.power-btn').click()
    await expect.poll(() => body).toMatchObject({ on: false })
  })

  // ── Speed ───────────────────────────────────────────────────────────────────

  test('speed preset 1 is highlighted when speed is 1', async ({ page }) => {
    const speedBtn = page.locator('.speed-presets button').filter({ hasText: '1' })
    await expect(speedBtn).toHaveAttribute('aria-pressed', 'true')
  })

  test('clicking speed preset 2 sends correct speed', async ({ page }) => {
    let body = null
    await page.route('**/api/command/speed', async route => {
      body = await route.request().postDataJSON()
      route.fulfill({ status: 204, body: '' })
    })

    await page.locator('.speed-presets button').filter({ hasText: '2' }).click()
    await expect.poll(() => body).toMatchObject({ speed: 2 })
  })

  test('manual speed mode shows slider when speed is 255', async ({ page }) => {
    await setupApiRoutes(page, {
      'GET /api/state': route => route.fulfill({ json: { ...CONNECTED_STATE, speed: 255, manual_speed: 100 } }),
    })
    await mockWebSocket(page)
    await page.goto('/')
    await expect(page.locator('.status-label')).toHaveText('Connected')
    await expect(page.locator('input[aria-label="Manual speed"]')).toBeVisible()
    await expect(page.locator('.speed-manual .speed-value')).toHaveText('100')
  })

  // ── Mode ────────────────────────────────────────────────────────────────────

  test('Ventilation mode button is active when operation_mode is 0', async ({ page }) => {
    const btn = page.locator('.mode-buttons button').filter({ hasText: 'Ventilation' })
    await expect(btn).toHaveAttribute('aria-pressed', 'true')
  })

  test('clicking Heat Recovery sends setMode with value 1', async ({ page }) => {
    let body = null
    await page.route('**/api/command/mode', async route => {
      body = await route.request().postDataJSON()
      route.fulfill({ status: 204, body: '' })
    })

    await page.locator('.mode-buttons button').filter({ hasText: 'Heat Recovery' }).click()
    await expect.poll(() => body).toMatchObject({ mode: 1 })
  })

  test('schedule toggle is OFF when weekly_schedule_enabled is false', async ({ page }) => {
    const toggleText = page.locator('.schedule-toggle .schedule-toggle-state')
    await expect(toggleText).toHaveText('OFF')
    await expect(page.locator('.schedule-toggle')).toHaveAttribute('aria-pressed', 'false')
  })

  test('clicking schedule toggle sends enableSchedule request', async ({ page }) => {
    let body = null
    await page.route('**/api/command/schedule_enable', async route => {
      body = await route.request().postDataJSON()
      route.fulfill({ status: 204, body: '' })
    })

    await page.locator('.schedule-toggle').click()
    await expect.poll(() => body).toMatchObject({ enabled: true })
  })
})
