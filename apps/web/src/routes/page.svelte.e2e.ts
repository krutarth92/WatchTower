import { expect, test } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test('redirects to the research shell', async ({ page }) => {
	const failedAssets: string[] = [];
	const pageErrors: string[] = [];
	page.on('response', (response) => {
		if (response.url().includes('/_app/') && !response.ok()) {
			failedAssets.push(`${response.status()} ${response.url()}`);
		}
	});
	page.on('pageerror', (error) => pageErrors.push(error.message));

	const navigation = await page.goto('/');
	await page.waitForLoadState('networkidle');

	await expect(page).toHaveURL(/\/search$/);
	await expect(page.getByRole('heading', { level: 1, name: /Track adversaries/ })).toBeVisible();
	await expect(page.getByRole('heading', { level: 2, name: 'Foundation telemetry' })).toBeVisible();
	await expect(page.getByText('Private by default')).toBeVisible();
	await expect(page.getByText('LOCAL / PRIVATE')).toBeVisible();

	const loadedPresentation = await page.evaluate(() => ({
		primaryColor: getComputedStyle(document.documentElement)
			.getPropertyValue('--color-primary')
			.trim(),
		stylesheets: document.styleSheets.length,
		javascriptResources: performance
			.getEntriesByType('resource')
			.filter((entry) => entry.name.includes('/_app/') && entry.name.endsWith('.js')).length
	}));
	expect(failedAssets).toEqual([]);
	expect(pageErrors).toEqual([]);
	expect(loadedPresentation.primaryColor).not.toBe('');
	expect(loadedPresentation.stylesheets).toBeGreaterThan(0);
	expect(loadedPresentation.javascriptResources).toBeGreaterThan(0);
	expect(navigation?.headers()['content-security-policy']).toContain("default-src 'self'");
	expect(navigation?.headers()['x-frame-options']).toBe('DENY');
	expect(navigation?.headers()['x-content-type-options']).toBe('nosniff');
});

test('preserves the research hierarchy at the minimum supported width', async ({ page }) => {
	await page.setViewportSize({ width: 320, height: 720 });
	await page.goto('/search');

	await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
	await expect(page.getByRole('heading', { level: 2, name: 'Foundation telemetry' })).toBeVisible();
	await expect(
		page.getByRole('heading', { level: 2, name: 'Built for evidence-first research' })
	).toBeVisible();

	const viewportFits = await page.evaluate(
		() => document.documentElement.scrollWidth <= innerWidth
	);
	expect(viewportFits).toBe(true);
});

test('component gallery is accessible and responsive at review widths', async ({ page }) => {
	for (const width of [320, 768, 1440]) {
		await page.setViewportSize({ width, height: 900 });
		await page.goto('/components');
		await page.waitForLoadState('networkidle');

		await expect(
			page.getByRole('heading', { level: 1, name: 'Intelligence interface primitives' })
		).toBeVisible();
		expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(
			true
		);

		const results = await new AxeBuilder({ page }).analyze();
		expect(results.violations, `${width}px accessibility violations`).toEqual([]);
	}
});
