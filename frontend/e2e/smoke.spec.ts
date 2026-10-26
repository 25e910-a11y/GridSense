import { test, expect } from '@playwright/test';

test.describe('Frontend Shell Smoke Test', () => {
  test('renders the application shell with genuine header landmarks and navigation', async ({ page }) => {
    // Navigate to root (which redirects to /login when unauthenticated)
    await page.goto('/');

    // Verify document title
    await expect(page).toHaveTitle(/IoT Power Monitoring & Fault Identification System/);

    // Verify URL resolves to /login
    await expect(page).toHaveURL(/\/login$/);

    // Verify header brand element exists and contains genuine product name
    const brandTitle = page.locator('.brand-title');
    await expect(brandTitle).toBeVisible();
    await expect(brandTitle).toContainText('IoT Power Monitoring');

    // Verify main content landmark is mounted
    const mainContent = page.locator('main.main-content');
    await expect(mainContent).toBeVisible();
  });
});
