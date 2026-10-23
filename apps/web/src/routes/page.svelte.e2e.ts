import { expect, test } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

const actorId = '20000000-0000-4000-8000-000000000001';
const partialActorId = '20000000-0000-4000-8000-000000000099';

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

test('moves from search into actor evolution and preserves opaque pagination', async ({ page }) => {
	await page.goto('/search?q=midnight');
	await page.getByRole('link', { name: 'Midnight Blizzard' }).click();

	await expect(page).toHaveURL(new RegExp(`/actors/${actorId}\\?fromSearch=`));
	await expect(page.getByRole('heading', { level: 1, name: 'Midnight Blizzard' })).toBeVisible();
	await expect(page.getByText('APT29')).toBeVisible();
	await expect(page.getByText('ORIGIN / IMPORTED')).toBeVisible();
	await expect(page.getByText('T1059.001').first()).toBeVisible();
	const backLink = page.getByRole('link', { name: 'Back to research results' });
	expect(await backLink.getAttribute('href')).toBe('/search?q=midnight');

	await page.getByText('Evidence · Northstar incident report, section 4').first().click();
	const sourceLink = page.getByRole('link', { name: 'Open source' }).first();
	await expect(sourceLink).toBeVisible();
	expect(await sourceLink.getAttribute('rel')).toBe('noopener noreferrer');

	await page.getByLabel('Intelligence').selectOption('observed');
	await page.getByRole('button', { name: 'Apply scope' }).click();
	await expect(page).toHaveURL(/intelligence_type=observed/);
	await expect(page).toHaveURL(/fromSearch=/);

	await page.getByRole('button', { name: 'Load earlier events' }).click();
	await expect(page.locator('.timeline-list article > header h3')).toHaveText([
		'PowerShell execution observed',
		'Earlier credential access'
	]);
	expect(new URL(page.url()).searchParams.has('cursor')).toBe(false);
});

test('retains actor identity when a secondary panel fails', async ({ page }) => {
	await page.goto(`/actors/${partialActorId}`);
	await expect(page.getByRole('heading', { level: 1, name: 'Partial Signal' })).toBeVisible();
	await expect(page.getByRole('heading', { name: 'References unavailable' })).toBeVisible();
	await expect(page.getByText(/mock-reference-500/)).toBeVisible();
	await expect(page.getByText('PowerShell execution observed')).toBeVisible();

	await page.getByRole('button', { name: 'Retry' }).last().click();
	await expect(page.getByRole('heading', { name: 'References unavailable' })).toBeVisible();
	await expect(page.getByRole('heading', { level: 1, name: 'Partial Signal' })).toBeVisible();

	await page.goto('/actors/not-a-valid-id');
	await expect(page.getByRole('heading', { name: 'Actor request unavailable' })).toBeVisible();
	await page.goto('/actors/20000000-0000-4000-8000-000000000404');
	await expect(page.getByRole('heading', { name: 'Published actor unavailable' })).toBeVisible();
	await expect(page.getByText('This published record is unavailable.')).toBeVisible();
});

test('actor workspace is accessible and responsive at review widths', async ({ page }) => {
	for (const width of [320, 768, 1440]) {
		await page.setViewportSize({ width, height: 1000 });
		await page.goto(`/actors/${actorId}?fromSearch=%2Fsearch%3Fq%3Dmidnight`);
		await page.waitForLoadState('networkidle');
		await expect(page.getByRole('heading', { level: 1, name: 'Midnight Blizzard' })).toBeVisible();
		expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(
			true
		);
		const results = await new AxeBuilder({ page }).analyze();
		expect(results.violations, `${width}px actor accessibility violations`).toEqual([]);
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
