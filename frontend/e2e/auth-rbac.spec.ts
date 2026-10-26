import { test, expect } from '@playwright/test';

// Common mock data fixtures
const MOCK_DEVICES = [
  { id: 1, device_id: 'PMU-TEST-001', name: 'Substation Feeder Unit', is_active: true },
];

const MOCK_DASHBOARD = {
  device_id: 1,
  system_status: 'Normal',
  phases: {
    R: { voltage: 230.1, current: 8.5, power: 1955, energy: 120.4, power_factor: 0.98, frequency: 50.0, temperature: 34.5 },
    Y: { voltage: 229.8, current: 8.6, power: 1976, energy: 121.1, power_factor: 0.98, frequency: 50.0, temperature: 34.8 },
    B: { voltage: 230.4, current: 8.4, power: 1935, energy: 119.8, power_factor: 0.98, frequency: 50.0, temperature: 34.2 },
  },
  open_faults: 0,
};

const MOCK_RELAYS = [
  {
    id: 1,
    device_id: 1,
    relay_number: 1,
    name: 'Feeder Main Contactor',
    gpio_pin: 18,
    is_active: true,
    is_on: false,
    commanded_state: false,
    actual_state: null,
    hardware_verified: false,
  },
];

// Helper to ensure we only intercept API calls (fetch/xhr), passing page navigation documents to Vite
const isApiCall = (req: import('@playwright/test').Request) => {
  const type = req.resourceType();
  return type === 'fetch' || type === 'xhr';
};

// Setup API route intercepts for deterministic, isolated testing
async function setupApiMocks(page: import('@playwright/test').Page) {
  // SPA fallback for routes that collide with Vite's backend proxy table
  await page.route(/http:\/\/localhost:\d+\/(faults|maintenance|relays|audit)(\/|\?|$)/, async (route) => {
    if (route.request().resourceType() === 'document') {
      const res = await page.request.get('/');
      await route.fulfill({
        status: 200,
        contentType: 'text/html',
        body: await res.body(),
      });
      return;
    }
    await route.fallback();
  });

  // Health check
  await page.route('**/health', async (route) => {
    if (!isApiCall(route.request())) return route.continue();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ status: 'ok', database: 'connected', is_live: true }),
    });
  });

  // Devices
  await page.route('**/devices/**', async (route) => {
    if (!isApiCall(route.request())) return route.continue();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(MOCK_DEVICES),
    });
  });

  // Campus hierarchy
  await page.route('**/locations/**', async (route) => {
    if (!isApiCall(route.request())) return route.continue();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ colleges: [], blocks: [], floors: [] }),
    });
  });

  // Live telemetry dashboard
  await page.route('**/dashboard/live*', async (route) => {
    if (!isApiCall(route.request())) return route.continue();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(MOCK_DASHBOARD),
    });
  });

  // Telemetry history
  await page.route('**/telemetry/**', async (route) => {
    if (!isApiCall(route.request())) return route.continue();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([]),
    });
  });

  // Relays API
  await page.route('**/relays/**', async (route) => {
    if (!isApiCall(route.request())) return route.continue();

    const request = route.request();
    const url = request.url();

    // Toggle on/off endpoint check
    if (url.includes('/on') || url.includes('/off')) {
      const authHeader = request.headers()['authorization'] || '';
      if (!authHeader.includes('test-jwt-admin')) {
        await route.fulfill({
          status: 403,
          contentType: 'application/json',
          body: JSON.stringify({ detail: "Operation not permitted. Required: admin" }),
        });
        return;
      }
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'success',
          message: 'Relay command accepted; awaiting physical contactor feedback',
          relay_id: 1,
          commanded_state: url.includes('/on'),
          is_on: url.includes('/on'),
          actual_state: null,
          hardware_verified: false,
        }),
      });
      return;
    }

    // Default GET relays
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(MOCK_RELAYS),
    });
  });

  // Faults API
  await page.route('**/faults/**', async (route) => {
    if (!isApiCall(route.request())) return route.continue();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([]),
    });
  });

  // Maintenance work orders API
  await page.route('**/maintenance/**', async (route) => {
    if (!isApiCall(route.request())) return route.continue();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([]),
    });
  });

  // Notifications API
  await page.route('**/notifications/**', async (route) => {
    if (!isApiCall(route.request())) return route.continue();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([]),
    });
  });

  // Audit logs API
  await page.route('**/audit/**', async (route) => {
    if (!isApiCall(route.request())) return route.continue();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([]),
    });
  });

  // Authentication endpoints
  await page.route('**/auth/login', async (route) => {
    if (!isApiCall(route.request())) return route.continue();

    const postData = route.request().postDataJSON() || {};
    const { username, password } = postData;

    if (password === 'ValidTestPass123!') {
      let role = 'operator';
      if (username === 'test_tech') role = 'technician';
      if (username === 'test_admin') role = 'admin';

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          access_token: `test-jwt-${role}`,
          token_type: 'bearer',
          role,
          username,
        }),
      });
    } else {
      await route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Invalid credentials' }),
      });
    }
  });

  await page.route('**/auth/me', async (route) => {
    if (!isApiCall(route.request())) return route.continue();

    const authHeader = route.request().headers()['authorization'] || '';
    if (authHeader.includes('test-jwt-operator')) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ authenticated: true, username: 'test_operator', role: 'operator' }),
      });
    } else if (authHeader.includes('test-jwt-technician')) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ authenticated: true, username: 'test_tech', role: 'technician' }),
      });
    } else if (authHeader.includes('test-jwt-shift_incharge')) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ authenticated: true, username: 'test_shift', role: 'shift_incharge' }),
      });
    } else if (authHeader.includes('test-jwt-engineer')) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ authenticated: true, username: 'test_engineer', role: 'electrical_engineer' }),
      });
    } else if (authHeader.includes('test-jwt-admin')) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ authenticated: true, username: 'test_admin', role: 'admin' }),
      });
    } else {
      await route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Not authenticated' }),
      });
    }
  });
}

test.describe('Authentication & RBAC Regression Test Suite', () => {
  test.beforeEach(async ({ page }) => {
    await setupApiMocks(page);
  });

  test.describe('1. Unauthenticated Route Protection', () => {
    test('direct navigation to /faults redirects unauthenticated user to /login with state', async ({ page }) => {
      await page.goto('/faults');
      await expect(page).toHaveURL(/\/login$/);
      await expect(page.locator('h1')).toContainText('IoT-Based Power Monitoring');
    });

    test('direct navigation to /maintenance redirects unauthenticated user to /login', async ({ page }) => {
      await page.goto('/maintenance');
      await expect(page).toHaveURL(/\/login$/);
      await expect(page.locator('h1')).toContainText('IoT-Based Power Monitoring');
    });

    test('direct navigation to /relays redirects unauthenticated user to /login', async ({ page }) => {
      await page.goto('/relays');
      await expect(page).toHaveURL(/\/login$/);
      await expect(page.locator('h1')).toContainText('IoT-Based Power Monitoring');
    });

    test('direct navigation to /audit redirects unauthenticated user to /login', async ({ page }) => {
      await page.goto('/audit');
      await expect(page).toHaveURL(/\/login$/);
      await expect(page.locator('h1')).toContainText('IoT-Based Power Monitoring');
    });

    test('unauthenticated direct navigation to /live and /history redirects to /login', async ({ page }) => {
      await page.goto('/live');
      await expect(page).toHaveURL(/\/login$/);
      await expect(page.locator('h1')).toContainText('IoT-Based Power Monitoring');

      await page.goto('/history');
      await expect(page).toHaveURL(/\/login$/);
      await expect(page.locator('h1')).toContainText('IoT-Based Power Monitoring');
    });
  });

  test.describe('2. Login Behavior & Credential Validation', () => {
    test('submitting invalid credentials displays accessible error alert without navigating away', async ({ page }) => {
      await page.goto('/login');

      const userInput = page.locator('#username-input');
      const passInput = page.locator('#password-input');
      await expect(userInput).toBeVisible();

      await userInput.fill('invalid_user');
      await expect(userInput).toHaveValue('invalid_user');
      await passInput.fill('WrongPassword999!');
      await expect(passInput).toHaveValue('WrongPassword999!');

      await page.locator('button[type="submit"]').click();

      const alert = page.locator('[role="alert"]');
      await expect(alert).toBeVisible();
      await expect(alert).toContainText('Invalid username or password');
      await expect(page).toHaveURL(/\/login$/);
    });

    test('successful operator login establishes session and redirects to intended destination', async ({ page }) => {
      // Navigate to /faults while unauthenticated (sets from: /faults)
      await page.goto('/faults');
      await expect(page).toHaveURL(/\/login$/);

      const userInput = page.locator('#username-input');
      const passInput = page.locator('#password-input');
      await expect(userInput).toBeVisible();

      await userInput.fill('test_operator');
      await expect(userInput).toHaveValue('test_operator');
      await passInput.fill('ValidTestPass123!');
      await expect(passInput).toHaveValue('ValidTestPass123!');

      await page.locator('button[type="submit"]').click();

      // Should automatically redirect to /faults
      await expect(page).toHaveURL(/\/faults$/);

      // Universal header should reflect authenticated state
      const userBadge = page.locator('.header-actions');
      await expect(userBadge).toContainText('test_operator');
      await expect(userBadge).toContainText('operator');
    });
  });

  test.describe('3. Role-Based Access Control (RBAC) Enforcement', () => {
    test('operator role is blocked from /maintenance with Role Unauthorized error', async ({ page }) => {
      await page.addInitScript(() => {
        sessionStorage.setItem('power_monitoring_access_token', 'test-jwt-operator');
      });

      await page.goto('/maintenance');

      // Verify RoleRoute Access Denied screen
      const deniedHeader = page.locator('h2');
      await expect(deniedHeader).toContainText('Access Denied: Role Unauthorized');

      const description = page.locator('p');
      await expect(description).toContainText('technician');
      await expect(description).toContainText('operator');

      // Test return navigation button
      const returnBtn = page.getByRole('link', { name: 'Return to Live Monitor' });
      await expect(returnBtn).toBeVisible();
      await returnBtn.click();
      await expect(page).toHaveURL(/\/live$/);
    });

    test('operator role is blocked from /audit with Role Unauthorized error', async ({ page }) => {
      await page.addInitScript(() => {
        sessionStorage.setItem('power_monitoring_access_token', 'test-jwt-operator');
      });

      await page.goto('/audit');
      await expect(page.locator('h2')).toContainText('Access Denied: Role Unauthorized');
      await expect(page.locator('p')).toContainText('admin');
    });

    test('technician role can access /maintenance but is blocked from /audit', async ({ page }) => {
      await page.addInitScript(() => {
        sessionStorage.setItem('power_monitoring_access_token', 'test-jwt-technician');
      });

      // Allowed on /maintenance
      await page.goto('/maintenance');
      await expect(page).toHaveURL(/\/maintenance$/);
      await expect(page.getByRole('heading', { name: /Maintenance Dispatch/i })).toBeVisible();

      // Blocked on /audit
      await page.goto('/audit');
      await expect(page.locator('h2')).toContainText('Access Denied: Role Unauthorized');
    });

    test('admin role can access all protected views without restriction', async ({ page }) => {
      await page.addInitScript(() => {
        sessionStorage.setItem('power_monitoring_access_token', 'test-jwt-admin');
      });

      // Access /audit
      await page.goto('/audit');
      await expect(page).toHaveURL(/\/audit$/);
      await expect(page.getByRole('heading', { name: /System Audit Trail/i })).toBeVisible();

      // Access /maintenance
      await page.goto('/maintenance');
      await expect(page).toHaveURL(/\/maintenance$/);
      await expect(page.getByRole('heading', { name: /Maintenance Dispatch/i })).toBeVisible();

      // Access /relays
      await page.goto('/relays');
      await expect(page).toHaveURL(/\/relays$/);
      await expect(page.getByRole('heading', { name: /Phase Solid-State Relay/i })).toBeVisible();
    });
  });

  test.describe('4. Role-Specific UI Permissions & Logout', () => {
    test('shift_incharge on /relays shows non-admin notice and blocks relay toggle command', async ({ page }) => {
      await page.addInitScript(() => {
        sessionStorage.setItem('power_monitoring_access_token', 'test-jwt-shift_incharge');
      });

      await page.goto('/relays');
      await expect(page).toHaveURL(/\/relays$/);

      // Verify toggle button is disabled and reflects non-admin restriction
      const restrictedBtn = page.getByRole('button', { name: /Restricted to Admin/i });
      await expect(restrictedBtn).toBeVisible();
      await expect(restrictedBtn).toBeDisabled();
    });

    test('admin on /relays has active command button enabled', async ({ page }) => {
      await page.addInitScript(() => {
        sessionStorage.setItem('power_monitoring_access_token', 'test-jwt-admin');
      });

      await page.goto('/relays');
      await expect(page).toHaveURL(/\/relays$/);

      // Verify toggle button is enabled for administrator
      const commandBtn = page.getByRole('button', { name: /Command ON/i });
      await expect(commandBtn).toBeVisible();
      await expect(commandBtn).toBeEnabled();
    });

    test('logging out clears session token and restores unauthenticated header view', async ({ page }) => {
      await page.goto('/login');
      await page.evaluate(() => {
        sessionStorage.setItem('power_monitoring_access_token', 'test-jwt-operator');
      });
      await page.goto('/live');

      await expect(page.locator('.header-actions')).toContainText('test_operator');

      // Click sign out in header using its aria-label
      const logoutBtn = page.getByRole('button', { name: 'Sign out' });
      await expect(logoutBtn).toBeVisible();
      await logoutBtn.click();

      // Verify header now displays "Sign In" link
      const signInLink = page.getByRole('link', { name: 'Sign In' });
      await expect(signInLink).toBeVisible();

      // Verify token cleared from sessionStorage
      const token = await page.evaluate(() => sessionStorage.getItem('power_monitoring_access_token'));
      expect(token).toBeNull();

      // Navigating to protected page now redirects to /login
      await page.goto('/faults');
      await expect(page).toHaveURL(/\/login$/);
    });
  });
});
