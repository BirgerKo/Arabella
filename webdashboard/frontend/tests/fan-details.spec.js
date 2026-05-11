import { test, expect } from '@playwright/test'
import { gotoConnected, openDetails, CONNECTED_STATE, setupApiRoutes, mockWebSocket } from './helpers.js'

const detailsModal = page => page.locator('[role="dialog"][aria-label="Fan details"]')

test.describe('Fan details modal', () => {
  test.beforeEach(async ({ page }) => {
    await gotoConnected(page)
  })

  test('Details button is disabled when not connected', async ({ page }) => {
    // 503 keeps deviceState null → deviceId undefined → DeviceHeader disables Details…
    await setupApiRoutes(page, {
      'GET /api/state': route => route.fulfill({ status: 503, json: { detail: 'Not connected' } }),
    })
    await mockWebSocket(page)
    await page.goto('/')
    await expect(page.locator('[role="dialog"][aria-label="Connect to device"]')).toBeVisible()
    await expect(page.getByRole('button', { name: 'Details…' })).toBeDisabled()
  })

  test('Details button opens fan details modal with device ID', async ({ page }) => {
    await openDetails(page)
    await expect(detailsModal(page).locator('.fan-details-name')).toHaveText('TESTFAN000000001')
    await expect(detailsModal(page).locator('.fan-details-ip')).toContainText('192.168.1.100')
  })

  test('close button dismisses the fan details modal', async ({ page }) => {
    await openDetails(page)
    await detailsModal(page).getByRole('button', { name: 'Close details' }).click()
    await expect(detailsModal(page)).not.toBeVisible()
  })

  // ── Boost ───────────────────────────────────────────────────────────────────

  test('boost button shows OFF when boost_active is false', async ({ page }) => {
    await openDetails(page)
    await expect(detailsModal(page).locator('.boost-btn')).toHaveText('Boost: OFF')
    await expect(detailsModal(page).locator('.boost-btn')).toHaveAttribute('aria-pressed', 'false')
  })

  test('clicking boost button sends setBoost request', async ({ page }) => {
    let body = null
    await page.route('**/api/command/boost', async route => {
      body = await route.request().postDataJSON()
      route.fulfill({ status: 204, body: '' })
    })

    await openDetails(page)
    await detailsModal(page).locator('.boost-btn').click()
    await expect.poll(() => body).toMatchObject({ on: true })
  })

  // ── Humidity ────────────────────────────────────────────────────────────────

  test('humidity sensor Off button is active when sensor is 0', async ({ page }) => {
    await openDetails(page)
    const offBtn = detailsModal(page).locator('.humidity-sensor-row button').filter({ hasText: 'Off' })
    await expect(offBtn).toHaveAttribute('aria-pressed', 'true')
  })

  test('clicking humidity sensor On sends correct request', async ({ page }) => {
    let body = null
    await page.route('**/api/command/humidity_sensor', async route => {
      body = await route.request().postDataJSON()
      route.fulfill({ status: 204, body: '' })
    })

    await openDetails(page)
    await detailsModal(page).locator('.humidity-sensor-row button').filter({ hasText: 'On' }).click()
    await expect.poll(() => body).toMatchObject({ sensor: 1 })
  })

  test('humidity threshold slider is hidden when sensor is Off', async ({ page }) => {
    await openDetails(page)
    await expect(detailsModal(page).locator('input[aria-label="Humidity threshold"]')).not.toBeVisible()
  })

  // ── RPM display ─────────────────────────────────────────────────────────────

  test('RPM section shows fan1 and fan2 values', async ({ page }) => {
    await openDetails(page)
    const rpmSection = detailsModal(page).locator('.rpm-card')
    await expect(rpmSection).toContainText('1200')
    await expect(rpmSection).toContainText('1150')
  })

  // ── RTC sync ────────────────────────────────────────────────────────────────

  test('Sync RTC button sends sync_rtc request', async ({ page }) => {
    let synced = false
    await page.route('**/api/command/sync_rtc', route => {
      synced = true
      route.fulfill({ status: 204, body: '' })
    })

    await openDetails(page)
    await detailsModal(page).getByRole('button', { name: 'Sync RTC' }).click()
    await expect.poll(() => synced).toBe(true)
  })

  test('RTC time is displayed in the schedule section', async ({ page }) => {
    await openDetails(page)
    await expect(detailsModal(page).locator('.rtc-display')).toContainText('10:30:00')
    await expect(detailsModal(page).locator('.rtc-display')).toContainText('2026-05-11')
  })
})
