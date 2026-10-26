import { test, expect } from '@playwright/test';

// Common test fixtures
const MOCK_DEVICES = [
  { id: 1, device_id: 'PMU-FEEDER-01', name: 'Substation Feeder Unit 01', is_active: true },
  { id: 2, device_id: 'PMU-TRANS-02', name: 'Transformer Secondary 02', is_active: true },
];

const DEVICE_1_TELEMETRY = {
  device_id: 1,
  device_name: 'Substation Feeder Unit 01',
  is_active: true,
  system_status: 'Normal',
  phases: {
    R: { voltage: 230.1, current: 8.5, power: 1955.0, energy: 120.4, power_factor: 0.98, frequency: 50.0, temperature: 34.5, data_quality: 'GOOD', sampled_at: '2026-10-22T08:00:00Z' },
    Y: { voltage: 229.8, current: 8.6, power: 1976.0, energy: 121.1, power_factor: 0.98, frequency: 50.0, temperature: 34.8, data_quality: 'GOOD', sampled_at: '2026-10-22T08:00:00Z' },
    B: { voltage: 230.4, current: 8.4, power: 1935.0, energy: 119.8, power_factor: 0.98, frequency: 50.0, temperature: 34.2, data_quality: 'GOOD', sampled_at: '2026-10-22T08:00:00Z' },
  },
  open_faults: [],
};

const DEVICE_2_TELEMETRY = {
  device_id: 2,
  device_name: 'Transformer Secondary 02',
  is_active: true,
  system_status: 'Normal',
  phases: {
    R: { voltage: 245.5, current: 12.0, power: 2946.0, energy: 210.0, power_factor: 0.96, frequency: 50.1, temperature: 38.0, data_quality: 'GOOD', sampled_at: '2026-10-22T08:00:00Z' },
    Y: { voltage: 244.8, current: 12.1, power: 2962.0, energy: 211.5, power_factor: 0.96, frequency: 50.1, temperature: 38.2, data_quality: 'GOOD', sampled_at: '2026-10-22T08:00:00Z' },
    B: { voltage: 246.0, current: 11.9, power: 2927.0, energy: 209.0, power_factor: 0.96, frequency: 50.1, temperature: 37.8, data_quality: 'GOOD', sampled_at: '2026-10-22T08:00:00Z' },
  },
  open_faults: [],
};

const isApiCall = (req: import('@playwright/test').Request) => {
  const type = req.resourceType();
  return type === 'fetch' || type === 'xhr';
};

// Base mock setup
async function setupStandardMocks(page: import('@playwright/test').Page, role: 'operator' | 'admin' = 'operator') {
  // Pre-seed session so protected telemetry routes mount
  await page.addInitScript((userRole) => {
    sessionStorage.setItem('power_monitoring_access_token', `test-jwt-${userRole}`);
  }, role);

  await page.route('**/auth/me', async (route) => {
    if (!isApiCall(route.request())) return route.continue();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        authenticated: true,
        username: role === 'admin' ? 'admin' : 'operator1',
        role: role,
        assigned_block_id: null,
        assigned_floor_id: null,
        permissions:
          role === 'admin'
            ? ['admin', 'switch_relays', 'view_live_metrics', 'view_faults', 'view_campus']
            : ['view_live_metrics', 'view_faults', 'view_campus'],
      }),
    });
  });

  // SPA fallback for routes that collide with Vite's backend proxy table
  await page.route(/http:\/\/localhost:\d+\/(faults|maintenance|relays|audit|history|campus)(\/|\?|$)/, async (route) => {
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

  // Health
  await page.route('**/health', async (route) => {
    if (!isApiCall(route.request())) return route.continue();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ status: 'ok', database: 'connected', is_live: true }),
    });
  });

  // Devices list
  await page.route('**/devices/**', async (route) => {
    if (!isApiCall(route.request())) return route.continue();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(MOCK_DEVICES),
    });
  });

  // Locations / Campus
  await page.route('**/locations/**', async (route) => {
    if (!isApiCall(route.request())) return route.continue();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ colleges: [], blocks: [], floors: [] }),
    });
  });

  // Telemetry history (default empty)
  await page.route('**/telemetry/**', async (route) => {
    if (!isApiCall(route.request())) return route.continue();
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([]),
    });
  });

  // Auxiliary defaults
  await page.route('**/faults/**', async (route) => {
    if (!isApiCall(route.request())) return route.continue();
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
  });

  await page.route('**/maintenance/**', async (route) => {
    if (!isApiCall(route.request())) return route.continue();
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
  });

  await page.route('**/notifications/**', async (route) => {
    if (!isApiCall(route.request())) return route.continue();
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
  });

  await page.route('**/audit/**', async (route) => {
    if (!isApiCall(route.request())) return route.continue();
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
  });
}

test.describe('Stage 3C.3: Device Switching, Telemetry Integrity & Offline Resilience', () => {

  // --------------------------------------------------------------------------
  // SECTION A: Device Switching & Race Conditions
  // --------------------------------------------------------------------------
  test.describe('A. Device Switching & Race Conditions', () => {
    test('out-of-order telemetry responses do not overwrite current device readings', async ({ page }) => {
      await setupStandardMocks(page);

      // Track how many times device 1 and device 2 are requested
      let device1Resolver: (() => void) | null = null;
      const device1Promise = new Promise<void>((resolve) => {
        device1Resolver = resolve;
      });

      await page.route('**/dashboard/live*', async (route) => {
        if (!isApiCall(route.request())) return route.continue();
        const url = route.request().url();

        if (url.includes('device_id=1')) {
          // Delay device 1 response until explicitly resolved
          await device1Promise;
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify(DEVICE_1_TELEMETRY),
          });
        } else if (url.includes('device_id=2')) {
          // Device 2 responds immediately
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify(DEVICE_2_TELEMETRY),
          });
        } else {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify(DEVICE_1_TELEMETRY),
          });
        }
      });

      await page.goto('/live');

      // Device 1 request is now in flight and pending. Switch to Device 2.
      const deviceSelect = page.locator('select[aria-label="Select Monitoring Device"]');
      await expect(deviceSelect).toBeVisible();
      await deviceSelect.selectOption('2');

      // Device 2 fulfills immediately; Phase R voltage for device 2 is 245.5 V
      await expect(page.getByText('245.5')).toBeVisible();

      // Now fulfill the delayed Device 1 response (230.1 V)
      if (device1Resolver) {
        (device1Resolver as () => void)();
      }

      // Allow event loop to process the resolved Device 1 response
      await page.waitForTimeout(300);

      // Verify Device 2's reading (245.5 V) remains displayed, and obsolete Device 1 reading (230.1 V) does NOT overwrite it
      await expect(page.getByText('245.5')).toBeVisible();
      await expect(page.getByText('230.1')).not.toBeVisible();
    });

    test('rapid device switching (1 -> 2 -> 1) commits only the freshest generation', async ({ page }) => {
      await setupStandardMocks(page);

      let reqCount = 0;
      await page.route('**/dashboard/live*', async (route) => {
        if (!isApiCall(route.request())) return route.continue();
        reqCount++;
        const currentReq = reqCount;
        const url = route.request().url();

        if (url.includes('device_id=1') && currentReq === 1) {
          // First request for device 1 is slow (simulates delayed transport)
          await new Promise((r) => setTimeout(r, 600));
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              ...DEVICE_1_TELEMETRY,
              phases: {
                ...DEVICE_1_TELEMETRY.phases,
                R: { ...DEVICE_1_TELEMETRY.phases.R, voltage: 210.0 },
              },
            }),
          });
        } else if (url.includes('device_id=2')) {
          await new Promise((r) => setTimeout(r, 100));
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify(DEVICE_2_TELEMETRY),
          });
        } else {
          // Fresh return for device 1
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              ...DEVICE_1_TELEMETRY,
              phases: {
                ...DEVICE_1_TELEMETRY.phases,
                R: { ...DEVICE_1_TELEMETRY.phases.R, voltage: 238.4 },
              },
            }),
          });
        }
      });

      await page.goto('/live');

      const deviceSelect = page.locator('select[aria-label="Select Monitoring Device"]');
      await expect(deviceSelect).toBeVisible();

      // Switch to Device 2, then quickly back to Device 1
      await deviceSelect.selectOption('2');
      await page.waitForTimeout(50);
      await deviceSelect.selectOption('1');

      // The fresh return for device 1 (238.4 V) should be displayed
      await expect(page.getByText('238.4')).toBeVisible();

      // Wait out any delayed requests
      await page.waitForTimeout(700);

      // Verify that stale 210.0 V was dropped and 238.4 V remains active
      await expect(page.getByText('238.4')).toBeVisible();
      await expect(page.getByText('210.0')).not.toBeVisible();
    });

    test('component cleanup on unmount terminates polling without unhandled errors', async ({ page }) => {
      await setupStandardMocks(page);

      let pendingResolver: (() => void) | null = null;
      await page.route('**/dashboard/live*', async (route) => {
        if (!isApiCall(route.request())) return route.continue();
        await new Promise<void>((r) => { pendingResolver = r; });
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(DEVICE_1_TELEMETRY),
        });
      });

      // Capture any unhandled page errors
      const errors: string[] = [];
      page.on('pageerror', (err) => errors.push(err.message));

      await page.goto('/live');

      // Navigate to /campus while telemetry poll is in flight
      await page.getByRole('link', { name: 'Campus' }).click();
      await expect(page).toHaveURL(/\/campus$/);

      // Fulfill the in-flight response after unmount
      if (pendingResolver) {
        (pendingResolver as () => void)();
      }
      await page.waitForTimeout(200);

      // Ensure no React unmounted component errors were thrown
      expect(errors).toHaveLength(0);
    });
  });

  // --------------------------------------------------------------------------
  // SECTION B: Telemetry Integrity
  // --------------------------------------------------------------------------
  test.describe('B. Telemetry Integrity', () => {
    test('partial 3-phase telemetry renders valid phases with units and marks missing phase OFFLINE', async ({ page }) => {
      await setupStandardMocks(page);

      // Device with only Phase R and Phase Y; Phase B completely omitted
      const partialTelemetry = {
        device_id: 1,
        device_name: 'Substation Feeder Unit 01',
        is_active: true,
        system_status: 'Offline',
        phases: {
          R: { voltage: 230.1, current: 8.5, power: 1955.0, energy: 120.4, power_factor: 0.98, frequency: 50.0, temperature: 34.5, data_quality: 'GOOD', sampled_at: '2026-10-22T08:00:00Z' },
          Y: { voltage: 229.8, current: 8.6, power: 1976.0, energy: 121.1, power_factor: 0.98, frequency: 50.0, temperature: 34.8, data_quality: 'GOOD', sampled_at: '2026-10-22T08:00:00Z' },
        },
        open_faults: [],
      };

      await page.route('**/dashboard/live*', async (route) => {
        if (!isApiCall(route.request())) return route.continue();
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(partialTelemetry),
        });
      });

      await page.goto('/live');

      // Phase R valid values and units
      const phaseRCard = page.locator('.phase-card.phase-r');
      await expect(phaseRCard).toBeVisible();
      await expect(phaseRCard.getByText('230.1')).toBeVisible();
      await expect(phaseRCard.getByText('1955.0')).toBeVisible();
      await expect(phaseRCard.getByText('GOOD')).toBeVisible();

      // Phase Y valid values
      const phaseYCard = page.locator('.phase-card.phase-y');
      await expect(phaseYCard).toBeVisible();
      await expect(phaseYCard.getByText('229.8')).toBeVisible();
      await expect(phaseYCard.getByText('GOOD')).toBeVisible();

      // Phase B missing -> OFFLINE badge, '--' values, 'N/A' timestamp
      const phaseBCard = page.locator('.phase-card.phase-b');
      await expect(phaseBCard).toBeVisible();
      await expect(phaseBCard.getByText('OFFLINE')).toBeVisible();
      await expect(phaseBCard.getByText('N/A')).toBeVisible();
    });

    test('entirely absent telemetry displays explicit Awaiting Telemetry banner', async ({ page }) => {
      await setupStandardMocks(page);

      const emptyTelemetry = {
        device_id: 1,
        device_name: 'Substation Feeder Unit 01',
        is_active: true,
        system_status: 'Offline',
        phases: {},
        open_faults: [],
      };

      await page.route('**/dashboard/live*', async (route) => {
        if (!isApiCall(route.request())) return route.continue();
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(emptyTelemetry),
        });
      });

      await page.goto('/live');

      // Awaiting telemetry alert banner
      const alertBanner = page.getByText(/Device Offline \/ Awaiting Telemetry/i);
      await expect(alertBanner).toBeVisible();
      await expect(page.getByText(/No active 3-phase telemetry records have been logged/i)).toBeVisible();

      // All 3 phase cards show OFFLINE
      const offlineBadges = page.locator('.phase-card').getByText('OFFLINE');
      await expect(offlineBadges).toHaveCount(3);
    });

    test('degraded or stale data quality displays STALE badge with warning token', async ({ page }) => {
      await setupStandardMocks(page);

      const staleTelemetry = {
        ...DEVICE_1_TELEMETRY,
        phases: {
          ...DEVICE_1_TELEMETRY.phases,
          R: { ...DEVICE_1_TELEMETRY.phases.R, data_quality: 'STALE' },
        },
      };

      await page.route('**/dashboard/live*', async (route) => {
        if (!isApiCall(route.request())) return route.continue();
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(staleTelemetry),
        });
      });

      await page.goto('/live');

      const phaseRCard = page.locator('.phase-card.phase-r');
      await expect(phaseRCard).toBeVisible();

      const stalePill = phaseRCard.getByText('STALE');
      await expect(stalePill).toBeVisible();
    });

    test('historical waveforms view handles empty records and server errors without crashing', async ({ page }) => {
      await setupStandardMocks(page);

      // 1. Empty telemetry history
      await page.route('**/telemetry/**', async (route) => {
        if (!isApiCall(route.request())) return route.continue();
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
      });

      await page.goto('/history');
      await expect(page.getByText('No time-series telemetry recorded for this device')).toBeVisible();

      // 2. Telemetry history server error (500)
      await page.route('**/telemetry/**', async (route) => {
        if (!isApiCall(route.request())) return route.continue();
        await route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Telemetry storage table read error' }),
        });
      });

      // Reload to re-fetch telemetry history with error mock
      await page.reload();

      await expect(page.getByText('Historical Telemetry Unavailable')).toBeVisible();
      await expect(page.getByText(/Telemetry storage table read error/i)).toBeVisible();
    });
  });

  // --------------------------------------------------------------------------
  // SECTION C: Offline & Polling Resilience
  // --------------------------------------------------------------------------
  test.describe('C. Offline & Polling Resilience', () => {
    test('backend disconnection displays API OFFLINE and recovers when backend reconnects', async ({ page }) => {
      await setupStandardMocks(page);

      let isBackendAlive = false;

      await page.route('**/health', async (route) => {
        if (!isApiCall(route.request())) return route.continue();
        if (!isBackendAlive) {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({ status: 'offline', is_live: false }),
          });
        } else {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({ status: 'ok', database: 'connected', is_live: true }),
          });
        }
      });

      await page.route('**/dashboard/live*', async (route) => {
        if (!isApiCall(route.request())) return route.continue();
        if (!isBackendAlive) {
          await route.abort('failed');
        } else {
          await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify(DEVICE_1_TELEMETRY),
          });
        }
      });

      await page.goto('/live');

      // Header indicates API OFFLINE
      await expect(page.getByText('API OFFLINE')).toBeVisible();

      // Main content shows disconnected notice
      await expect(page.getByText('Telemetry Stream Unavailable — Backend Disconnected')).toBeVisible();

      // Now backend reconnects
      isBackendAlive = true;

      // Trigger re-poll by navigating between tabs or waiting for dynamic poll
      await page.getByRole('link', { name: 'Campus' }).click();
      await page.getByRole('link', { name: 'Live Monitor' }).click();

      // Header transitions to API LIVE and phase cards load
      await expect(page.getByText('API LIVE')).toBeVisible();
      await expect(page.locator('.phase-card.phase-r').getByText('230.1')).toBeVisible();
    });

    test('HTTP 500 error on live dashboard is handled safely without white screen', async ({ page }) => {
      await setupStandardMocks(page);

      await page.route('**/dashboard/live*', async (route) => {
        if (!isApiCall(route.request())) return route.continue();
        await route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Internal Database Connection Lost' }),
        });
      });

      await page.goto('/live');

      // The shell header remains fully intact and responsive
      const brand = page.locator('.brand-title');
      await expect(brand).toBeVisible();
      await expect(brand).toContainText('IoT Power Monitoring');

      // User can still navigate to other views without application freeze
      await page.getByRole('link', { name: 'Campus' }).click();
      await expect(page).toHaveURL(/\/campus$/);
    });
  });

  // --------------------------------------------------------------------------
  // SECTION D: Solid-State Relay Truthfulness
  // --------------------------------------------------------------------------
  test.describe('D. Solid-State Relay Truthfulness', () => {
    test('commanded state is strictly separated from unverified physical contactor feedback', async ({ page }) => {
      await setupStandardMocks(page, 'admin');

      const MOCK_UNVERIFIED_RELAY = [
        {
          id: 1,
          device_id: 1,
          relay_number: 1,
          name: 'Main 3-Phase Contactor',
          gpio_pin: 18,
          is_active: true,
          is_on: true,
          commanded_state: true,
          actual_state: null, // Feedback pending from hardware telemetry
          hardware_verified: false,
        },
      ];

      await page.route('**/relays/**', async (route) => {
        if (!isApiCall(route.request())) return route.continue();
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(MOCK_UNVERIFIED_RELAY),
        });
      });

      await page.goto('/relays');

      // Commanded state shows HIGH
      await expect(page.getByText('HIGH (1 - Signal Sent)')).toBeVisible();

      // Hardware feedback explicitly states UNVERIFIED
      await expect(page.getByText('UNVERIFIED (Pending Telemetry)')).toBeVisible();

      // Status pill marks state as COMMANDED: ON (Pending Telemetry)
      await expect(page.getByText('COMMANDED: ON (Pending Telemetry)')).toBeVisible();

      // Verify it does NOT claim verified closed
      await expect(page.getByText('VERIFIED CLOSED')).not.toBeVisible();
    });

    test('relay actuation command rejection displays error and maintains honest state', async ({ page }) => {
      await setupStandardMocks(page, 'admin');

      const MOCK_OFF_RELAY = [
        {
          id: 1,
          device_id: 1,
          relay_number: 1,
          name: 'Main 3-Phase Contactor',
          gpio_pin: 18,
          is_active: true,
          is_on: false,
          commanded_state: false,
          actual_state: false,
          hardware_verified: true,
        },
      ];

      await page.route('**/relays/**', async (route) => {
        if (!isApiCall(route.request())) return route.continue();
        const url = route.request().url();

        if (url.includes('/on') || url.includes('/off')) {
          // Contactor actuation fails
          await route.fulfill({
            status: 500,
            contentType: 'application/json',
            body: JSON.stringify({ detail: 'SSR Controller Gateway Timeout (Contactor Unresponsive)' }),
          });
          return;
        }

        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(MOCK_OFF_RELAY),
        });
      });

      await page.goto('/relays');

      // Click Command ON
      const commandBtn = page.getByRole('button', { name: /Command ON \(Close Circuit\)/i });
      await expect(commandBtn).toBeVisible();
      await commandBtn.click();

      // Error banner appears with backend detail
      await expect(page.getByText(/Relay Command Failed: SSR Controller Gateway Timeout/i)).toBeVisible();

      // Relay button returns from transmitting state and remains OFF
      await expect(commandBtn).toBeVisible();

      // Hardware feedback remains VERIFIED OPEN (not closed)
      await expect(page.getByText('VERIFIED OPEN')).toBeVisible();
      await expect(page.getByText('VERIFIED CLOSED')).not.toBeVisible();
    });

    test('verified physical contactor feedback correctly confirms circuit closure when telemetry validates', async ({ page }) => {
      await setupStandardMocks(page, 'admin');

      const MOCK_VERIFIED_RELAY = [
        {
          id: 1,
          device_id: 1,
          relay_number: 1,
          name: 'Main 3-Phase Contactor',
          gpio_pin: 18,
          is_active: true,
          is_on: true,
          commanded_state: true,
          actual_state: true, // Physical sensor telemetry confirmed current flowing
          hardware_verified: true,
        },
      ];

      await page.route('**/relays/**', async (route) => {
        if (!isApiCall(route.request())) return route.continue();
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(MOCK_VERIFIED_RELAY),
        });
      });

      await page.goto('/relays');

      // When telemetry confirms closure, Hardware Feedback displays VERIFIED CLOSED
      await expect(page.getByText('VERIFIED CLOSED')).toBeVisible();
    });
  });
});
