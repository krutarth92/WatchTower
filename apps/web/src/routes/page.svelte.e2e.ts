import { expect, test } from '@playwright/test';

test('redirects to the research shell', async ({ page }) => {
	const failedAssets: string[] = [];
	const pageErrors: string[] = [];
	page.on('response', (response) => {
		if (response.url().includes('/_app/') && !response.ok()) {
			failedAssets.push(`${response.status()} ${response.url()}`);
		}
	});
	page.on('pageerror', (error) => pageErrors.push(error.message));

	await page.goto('/');
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
