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
	await expect(page.getByRole('heading', { level: 1, name: 'Research search' })).toBeVisible();
	await expect(page.getByText('PUBLISHED INTELLIGENCE INDEX')).toBeVisible();
	await expect(page.getByText('PUBLISHED ONLY')).toBeVisible();
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

	await expect(page.getByRole('heading', { level: 1, name: 'Research search' })).toBeVisible();
	await expect(
		page.getByRole('heading', { level: 2, name: 'Enter a signal to begin' })
	).toBeVisible();

	const viewportFits = await page.evaluate(
		() => document.documentElement.scrollWidth <= innerWidth
	);
	expect(viewportFits).toBe(true);
});

test('runs a reproducible search, filters it and appends opaque cursor results', async ({
	page
}) => {
	await page.goto('/search');
	const query = page.getByLabel('Search published intelligence');
	await query.fill('midnight');
	await query.press('Enter');

	await expect(page).toHaveURL(/\/search\?q=midnight$/);
	await expect(page.getByRole('heading', { level: 2, name: '“midnight”' })).toBeVisible();
	await expect(page.locator('.result-list article h2')).toHaveText([
		'Midnight Blizzard',
		'PowerShell'
	]);
	await expect(page.locator('.result-list article .chip').first()).toHaveText('OBSERVED');

	await page.getByRole('button', { name: 'Filters' }).click();
	const dialog = page.getByRole('dialog', { name: 'Filter published intelligence' });
	await expect(dialog).toBeVisible();
	await expect(dialog.getByRole('checkbox', { name: 'actor' })).toBeFocused();
	await dialog.getByRole('checkbox', { name: 'technique' }).check();
	await dialog.getByRole('button', { name: 'Apply filters' }).click();
	await expect(page).toHaveURL(/q=midnight&entity_type=technique/);

	await page.getByRole('button', { name: 'Load more results' }).click();
	await expect(page.locator('.result-list article h2')).toHaveText([
		'Midnight Blizzard',
		'PowerShell',
		'Third source result'
	]);
	expect(new URL(page.url()).searchParams.has('cursor')).toBe(false);
});

test('shows local validation, no-match and safe API error states', async ({ page }) => {
	await page.goto('/search?q=x');
	await expect(page.getByRole('heading', { name: 'Correct the query scope' })).toBeVisible();
	await expect(page.getByText('Enter at least two non-whitespace characters.')).toBeVisible();

	await page.goto('/search?q=nothing');
	await expect(page.getByText('No published matches for “nothing”')).toBeVisible();

	await page.goto('/search?q=rate-limited');
	await expect(page.getByText('Search rate limited')).toBeVisible();
	await expect(page.getByText(/mock-429/)).toBeVisible();
	await expect(page.getByText('Mock detail.')).toHaveCount(0);

	await page.goto('/search?q=server-error');
	await expect(page.getByText('Search unavailable')).toBeVisible();
	await expect(page.getByText(/mock-500/)).toBeVisible();
	await expect(page.getByText('Mock detail.')).toHaveCount(0);
});

test('search results are accessible and responsive at review widths', async ({ page }) => {
	for (const width of [320, 768, 1440]) {
		await page.setViewportSize({ width, height: 900 });
		await page.goto('/search?q=midnight');
		await page.waitForLoadState('networkidle');
		await expect(page.getByRole('heading', { level: 2, name: '“midnight”' })).toBeVisible();
		expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(
			true
		);
		const results = await new AxeBuilder({ page }).analyze();
		expect(results.violations, `${width}px search accessibility violations`).toEqual([]);
	}
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
