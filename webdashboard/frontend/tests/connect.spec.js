import { test, expect } from '@playwright/test'
import { setupApiRoutes, mockWebSocket, gotoDisconnected, gotoConnected, CONNECTED_STATE, DISCOVERED } from './helpers.js'

const dialog = page => page.locator('[role="dialog"][aria-label="Connect to device"]')

test.describe('Connect / disconnect flow', () => {
  test('shows connect dialog on startup when device is not reachable', async ({ page }) => {
    await gotoDisconnected(page)
    await expect(dialog(page)).toBeVisible()
    await expect(dialog(page).getByRole('heading')).toHaveText('Connect to Device')
  })

  test('populates discovered devices list from scan on mount', async ({ page }) => {
    await gotoDisconnected(page)
    const item = dialog(page).locator('.device-item')
    await expect(item).toHaveCount(1)
    await expect(item).toContainText('TESTFAN000000001')
    await expect(item).toContainText('192.168.1.100')
  })

  test('rescan button triggers a fresh device scan', async ({ page }) => {
    let scanCount = 0
    await setupApiRoutes(page, {
      'GET /api/state': route => route.fulfill({ status: 503, json: { detail: 'Not connected' } }),
      'GET /api/devices': route => { scanCount++; route.fulfill({ json: DISCOVERED }) },
    })
    await mockWebSocket(page)
    await page.goto('/')
    await expect(dialog(page)).toBeVisible()

    const countBefore = scanCount
    await dialog(page).getByRole('button', { name: /Rescan/ }).click()
    await expect(dialog(page).locator('.device-item')).toHaveCount(1)
    expect(scanCount).toBeGreaterThan(countBefore)
  })

  test('clicking a discovered device connects with default password', async ({ page }) => {
    let connectBody = null
    await setupApiRoutes(page, {
      'GET /api/state': route => route.fulfill({ status: 503, json: { detail: 'Not connected' } }),
      'POST /api/connect': async route => {
        connectBody = await route.request().postDataJSON()
        route.fulfill({ json: CONNECTED_STATE })
      },
    })
    await mockWebSocket(page)
    await page.goto('/')
    await expect(dialog(page)).toBeVisible()

    await dialog(page).locator('.device-item').first().click()
    await expect(page.locator('.status-label')).toHaveText('Connected')

    expect(connectBody).toMatchObject({ ip: '192.168.1.100', device_id: 'TESTFAN000000001', password: '1111' })
  })

  test('connects via manual form with custom credentials', async ({ page }) => {
    let connectBody = null
    await setupApiRoutes(page, {
      'GET /api/state': route => route.fulfill({ status: 503, json: { detail: 'Not connected' } }),
      'POST /api/connect': async route => {
        connectBody = await route.request().postDataJSON()
        route.fulfill({ json: CONNECTED_STATE })
      },
    })
    await mockWebSocket(page)
    await page.goto('/')
    await expect(dialog(page)).toBeVisible()

    await dialog(page).getByPlaceholder('IP address').fill('10.0.0.5')
    await dialog(page).getByPlaceholder('Device ID').fill('MYFAN001')
    await dialog(page).getByPlaceholder(/Password/).fill('9999')
    await dialog(page).getByRole('button', { name: 'Connect' }).click()
    await expect(page.locator('.status-label')).toHaveText('Connected')

    expect(connectBody).toMatchObject({ ip: '10.0.0.5', device_id: 'MYFAN001', password: '9999' })
  })

  test('displays error message on connection failure', async ({ page }) => {
    await setupApiRoutes(page, {
      'GET /api/state': route => route.fulfill({ status: 503, json: { detail: 'Not connected' } }),
      'POST /api/connect': route => route.fulfill({ status: 502, json: { detail: 'Device unreachable' } }),
    })
    await mockWebSocket(page)
    await page.goto('/')
    await expect(dialog(page)).toBeVisible()

    await dialog(page).locator('.device-item').first().click()
    await expect(dialog(page).locator('.connect-error')).toContainText('Device unreachable')
  })

  test('switch button re-opens connect dialog from the dashboard', async ({ page }) => {
    await gotoConnected(page)
    await expect(dialog(page)).not.toBeVisible()

    await page.getByRole('button', { name: 'Switch…' }).click()
    await expect(dialog(page)).toBeVisible()
  })
})
