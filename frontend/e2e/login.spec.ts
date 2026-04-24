import { test, expect } from '@playwright/test'

test.describe('Login flow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login')
  })

  test('renders sign-in form', async ({ page }) => {
    await expect(page.getByText('Sign in')).toBeVisible()
    await expect(page.getByPlaceholder('admin@priceonn.com')).toBeVisible()
    await expect(page.getByPlaceholder('••••••••')).toBeVisible()
    await expect(page.getByRole('button', { name: /sign in/i })).toBeEnabled()
  })

  test('shows error on invalid credentials', async ({ page }) => {
    // Mock the API response for login failure
    await page.route('**/api/auth/login', async (route) => {
      await route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Invalid credentials' }),
      })
    })

    await page.getByPlaceholder('admin@priceonn.com').fill('bad@example.com')
    await page.getByPlaceholder('••••••••').fill('wrongpass')
    await page.getByRole('button', { name: /sign in/i }).click()

    await expect(page.getByText('Invalid credentials. Please try again.')).toBeVisible()
  })

  test('redirects to dashboard on successful login', async ({ page }) => {
    await page.route('**/api/auth/login', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          access_token: 'fake-access-token',
          refresh_token: 'fake-refresh-token',
          token_type: 'bearer',
          requires_totp: false,
          totp_token: null,
        }),
      })
    })

    await page.route('**/api/auth/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: '00000000-0000-0000-0000-000000000001',
          email: 'admin@priceonn.com',
          role: 'admin',
          is_active: true,
          created_at: '2024-01-01T00:00:00Z',
        }),
      })
    })

    // Mock dashboard data to avoid real API calls
    await page.route('**/api/**', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: '{}' })
    })

    await page.getByPlaceholder('admin@priceonn.com').fill('admin@priceonn.com')
    await page.getByPlaceholder('••••••••').fill('password')
    await page.getByRole('button', { name: /sign in/i }).click()

    await expect(page).toHaveURL(/\/dashboard/)
  })

  test('shows TOTP step when 2FA is required', async ({ page }) => {
    await page.route('**/api/auth/login', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          access_token: null,
          refresh_token: null,
          token_type: 'bearer',
          requires_totp: true,
          totp_token: 'challenge-token-abc',
        }),
      })
    })

    await page.getByPlaceholder('admin@priceonn.com').fill('admin@priceonn.com')
    await page.getByPlaceholder('••••••••').fill('password')
    await page.getByRole('button', { name: /sign in/i }).click()

    await expect(page.getByText('Two-Factor Auth')).toBeVisible()
    await expect(page.getByPlaceholder('000000')).toBeVisible()
  })

  test('back button returns from TOTP to login', async ({ page }) => {
    await page.route('**/api/auth/login', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          access_token: null,
          refresh_token: null,
          token_type: 'bearer',
          requires_totp: true,
          totp_token: 'challenge-token-abc',
        }),
      })
    })

    await page.getByPlaceholder('admin@priceonn.com').fill('admin@priceonn.com')
    await page.getByPlaceholder('••••••••').fill('password')
    await page.getByRole('button', { name: /sign in/i }).click()

    await expect(page.getByText('Two-Factor Auth')).toBeVisible()
    await page.getByText('← Back to login').click()
    await expect(page.getByText('Sign in')).toBeVisible()
  })
})
