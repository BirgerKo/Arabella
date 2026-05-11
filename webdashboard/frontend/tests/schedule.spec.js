import { test, expect } from '@playwright/test'
import { gotoConnected, openDetails, SCHEDULE } from './helpers.js'

const scheduleModal = page => page.locator('[role="dialog"][aria-label="Weekly schedule editor"]')
const detailsModal  = page => page.locator('[role="dialog"][aria-label="Fan details"]')

async function openSchedule(page) {
  await openDetails(page)
  await detailsModal(page).getByRole('button', { name: 'Edit…' }).click()
  await expect(scheduleModal(page)).toBeVisible()
}

test.describe('Schedule editor', () => {
  test.beforeEach(async ({ page }) => {
    await gotoConnected(page)
  })

  test('shows loading state before schedule data arrives', async ({ page }) => {
    // Delay the schedule response so we can observe the loading message
    await page.route('**/api/command/schedule', async route => {
      await new Promise(r => setTimeout(r, 500))
      route.fulfill({ json: SCHEDULE })
    })

    await openDetails(page)
    await detailsModal(page).getByRole('button', { name: 'Edit…' }).click()
    await expect(scheduleModal(page)).toBeVisible()
    await expect(scheduleModal(page)).toContainText('Loading schedule from device')
  })

  test('shows 8 day rows and 4 period columns after schedule loads', async ({ page }) => {
    await openSchedule(page)
    // Wait for the full table (loading message disappears)
    await expect(scheduleModal(page).locator('table.schedule-table')).toBeVisible()

    const rows = scheduleModal(page).locator('tbody tr')
    await expect(rows).toHaveCount(8)

    // Each row has 4 period cells + 1 day label cell
    const firstRowCells = rows.first().locator('td')
    await expect(firstRowCells).toHaveCount(5)
  })

  test('day labels are correct', async ({ page }) => {
    await openSchedule(page)
    await expect(scheduleModal(page).locator('table.schedule-table')).toBeVisible()

    const dayLabels = scheduleModal(page).locator('.day-label')
    await expect(dayLabels.nth(0)).toHaveText('Weekdays')
    await expect(dayLabels.nth(1)).toHaveText('Monday')
    await expect(dayLabels.nth(7)).toHaveText('Sunday')
  })

  test('period cells are pre-populated from schedule data', async ({ page }) => {
    await openSchedule(page)
    await expect(scheduleModal(page).locator('table.schedule-table')).toBeVisible()

    // First period of first day should have speed=1 (from mock SCHEDULE)
    const firstCell = scheduleModal(page).locator('tbody tr').first().locator('.period-speed').first()
    await expect(firstCell).toHaveValue('1')
  })

  test('Apply to device sends 32 schedule_period requests', async ({ page }) => {
    const requests = []
    await page.route('**/api/command/schedule_period', async route => {
      requests.push(await route.request().postDataJSON())
      route.fulfill({ status: 204, body: '' })
    })

    await openSchedule(page)
    await expect(scheduleModal(page).locator('table.schedule-table')).toBeVisible()

    await scheduleModal(page).getByRole('button', { name: 'Apply to device' }).click()

    // 8 days × 4 periods = 32 calls
    await expect.poll(() => requests.length, { timeout: 10_000 }).toBe(32)

    // Verify first and last request structure
    expect(requests[0]).toMatchObject({ day: 0, period: 1 })
    expect(requests[31]).toMatchObject({ day: 7, period: 4 })
  })

  test('Close button dismisses schedule editor without sending API calls', async ({ page }) => {
    let periodCallCount = 0
    await page.route('**/api/command/schedule_period', route => {
      periodCallCount++
      route.fulfill({ status: 204, body: '' })
    })

    await openSchedule(page)
    await expect(scheduleModal(page).locator('table.schedule-table')).toBeVisible()

    await scheduleModal(page).getByRole('button', { name: 'Close' }).click()
    await expect(scheduleModal(page)).not.toBeVisible()
    expect(periodCallCount).toBe(0)
  })
})
