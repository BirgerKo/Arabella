import { test, expect } from '@playwright/test'
import { gotoConnected, openDetails, SCENARIOS, QUICK_SLOTS } from './helpers.js'

const detailsModal = page => page.locator('[role="dialog"][aria-label="Fan details"]')
const saveModal    = page => page.locator('[role="dialog"][aria-label="Save scenario"]')

test.describe('Scenario manager', () => {
  test.beforeEach(async ({ page }) => {
    await gotoConnected(page)
    await openDetails(page)
  })

  test('scenario list shows all saved scenarios', async ({ page }) => {
    const list = detailsModal(page).locator('.scenario-list .scenario-name')
    await expect(list).toHaveCount(SCENARIOS.length)
    await expect(list.nth(0)).toHaveText('Night')
    await expect(list.nth(1)).toHaveText('Boost')
  })

  test('quick slot dropdown shows current assignment for Night scenario', async ({ page }) => {
    // QUICK_SLOTS has Night in slot 0 → Q1
    const nightSlotSelect = detailsModal(page).locator('select[aria-label="Quick slot for Night"]')
    await expect(nightSlotSelect).toHaveValue('Q1')
  })

  test('opening Scenario dropdown shows Create new option', async ({ page }) => {
    await detailsModal(page).locator('.save-scenario-btn').click()
    await expect(detailsModal(page).locator('.scenario-menu')).toBeVisible()
    await expect(detailsModal(page).locator('.scenario-menu-item').first()).toContainText('Create new scenario')
  })

  test('clicking Create new scenario shows the save scenario modal', async ({ page }) => {
    await detailsModal(page).locator('.save-scenario-btn').click()
    await detailsModal(page).getByRole('button', { name: 'Create new scenario…' }).click()
    await expect(saveModal(page)).toBeVisible()
  })

  test('saving a new scenario calls POST /api/scenarios with the name', async ({ page }) => {
    let body = null
    await page.route('**/api/scenarios', async route => {
      if (route.request().method() === 'POST') {
        body = await route.request().postDataJSON()
        route.fulfill({ json: SCENARIOS[0] })
      } else {
        route.fulfill({ json: SCENARIOS })
      }
    })

    await detailsModal(page).locator('.save-scenario-btn').click()
    await detailsModal(page).getByRole('button', { name: 'Create new scenario…' }).click()
    await expect(saveModal(page)).toBeVisible()
    await saveModal(page).locator('#scenario-name').fill('Morning')
    await saveModal(page).getByRole('button', { name: 'Save' }).click()

    await expect.poll(() => body).toMatchObject({ name: 'Morning' })
  })

  test('save button is disabled when scenario name is empty', async ({ page }) => {
    await detailsModal(page).locator('.save-scenario-btn').click()
    await detailsModal(page).getByRole('button', { name: 'Create new scenario…' }).click()
    await expect(saveModal(page)).toBeVisible()
    await expect(saveModal(page).getByRole('button', { name: 'Save' })).toBeDisabled()
  })

  test('play button sends apply request for the scenario', async ({ page }) => {
    let appliedName = null
    await page.route('**/api/scenarios/**/apply', route => {
      const path = new URL(route.request().url()).pathname
      appliedName = decodeURIComponent(path.split('/')[3])
      route.fulfill({ status: 204, body: '' })
    })

    await detailsModal(page).getByRole('button', { name: 'Apply Night' }).click()
    await expect.poll(() => appliedName).toBe('Night')
  })

  test('delete button sends DELETE request for the scenario', async ({ page }) => {
    let deletedName = null
    await page.route('**/api/scenarios/**', route => {
      if (route.request().method() === 'DELETE') {
        const path = new URL(route.request().url()).pathname
        deletedName = decodeURIComponent(path.split('/')[3])
        route.fulfill({ status: 204, body: '' })
      } else {
        route.continue()
      }
    })

    await detailsModal(page).getByRole('button', { name: 'Delete Night' }).click()
    await expect.poll(() => deletedName).toBe('Night')
  })
})

test.describe('Quick scenario slots', () => {
  test.beforeEach(async ({ page }) => {
    await gotoConnected(page)
  })

  test('Q1 slot shows the assigned scenario name', async ({ page }) => {
    // QUICK_SLOTS has 'Night' in slot 0
    const q1 = page.locator('.quick-slot').nth(0)
    await expect(q1).toContainText('Night')
  })

  test('Q2 and Q3 slots are empty and disabled', async ({ page }) => {
    const q2 = page.locator('.quick-slot').nth(1)
    const q3 = page.locator('.quick-slot').nth(2)
    await expect(q2).toBeDisabled()
    await expect(q3).toBeDisabled()
  })

  test('clicking Q1 sends apply scenario request', async ({ page }) => {
    let applied = null
    await page.route('**/api/scenarios/**/apply', route => {
      const path = new URL(route.request().url()).pathname
      applied = decodeURIComponent(path.split('/')[3])
      route.fulfill({ status: 204, body: '' })
    })

    await page.locator('.quick-slot').nth(0).click()
    await expect.poll(() => applied).toBe('Night')
  })

  test('assigning a scenario to a slot calls setQuickSlots', async ({ page }) => {
    let quickSlotsBody = null
    await page.route('**/api/scenarios/quick-slots/**', async route => {
      if (route.request().method() === 'PUT') {
        quickSlotsBody = await route.request().postDataJSON()
        route.fulfill({ json: QUICK_SLOTS })
      } else {
        route.fulfill({ json: QUICK_SLOTS })
      }
    })

    await openDetails(page)
    const boostSlotSelect = detailsModal(page).locator('select[aria-label="Quick slot for Boost"]')
    await boostSlotSelect.selectOption('Q2')

    await expect.poll(() => quickSlotsBody).not.toBeNull()
    // Q2 is index 1; Boost should be in slot 1
    expect(quickSlotsBody.slots[1]).toBe('Boost')
  })
})
