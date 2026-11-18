import { expect, test } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

const actorId = '20000000-0000-4000-8000-000000000001';
const partialActorId = '20000000-0000-4000-8000-000000000099';

test('loads the public home with real module navigation and platform update', async ({ page }) => {
	const failedAssets: string[] = [];
	const pageErrors: string[] = [];
	const consoleErrors: string[] = [];
	page.on('response', (response) => {
		if (response.url().includes('/_app/') && !response.ok()) {
			failedAssets.push(`${response.status()} ${response.url()}`);
		}
	});
	page.on('pageerror', (error) => pageErrors.push(error.message));
	page.on('console', (message) => {
		if (message.type() === 'error') consoleErrors.push(message.text());
	});

	const navigation = await page.goto('/');
	await page.waitForLoadState('networkidle');

	await expect(page).toHaveURL(/\/$/);
	await expect(page.getByRole('heading', { level: 1, name: /Track the adversary/ })).toBeVisible();
	await expect(page.getByText('Indicators and CVEs now reveal related actors')).toBeVisible();
	await expect(page.getByRole('heading', { level: 2, name: 'Latest intelligence' })).toBeVisible();
	await expect(
		page.getByRole('link', { name: 'Credential access activity evolves' })
	).toBeVisible();
	for (const destination of [
		'Home',
		'Intelligence',
		'Actors',
		'Evolution',
		'Research',
		'Technical'
	]) {
		await expect(
			page
				.getByRole('navigation', { name: 'Primary navigation' })
				.getByRole('link', { name: destination })
		).toBeVisible();
	}
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
	expect(consoleErrors).toEqual([]);
	expect(loadedPresentation.primaryColor).not.toBe('');
	expect(loadedPresentation.stylesheets).toBeGreaterThan(0);
	expect(loadedPresentation.javascriptResources).toBeGreaterThan(0);
	const contentSecurityPolicy = navigation?.headers()['content-security-policy'];
	expect(contentSecurityPolicy).toContain("default-src 'self'");
	expect(contentSecurityPolicy).toContain(
		"style-src 'self' 'unsafe-hashes' 'sha256-S8qMpvofolR8Mpjy4kQvEm7m1q8clzU4dfDH0AmvZjo='"
	);
	expect(navigation?.headers()['x-frame-options']).toBe('DENY');
	expect(navigation?.headers()['x-content-type-options']).toBe('nosniff');
});

test('opens the platform update archive and each primary module', async ({ page }) => {
	await page.goto('/updates');
	await expect(page.getByRole('heading', { level: 1, name: 'Platform updates' })).toBeVisible();
	await expect(page.getByText('Indicators and CVEs now reveal related actors')).toBeVisible();

	for (const [path, heading] of [
		['/advisories', 'Intelligence'],
		['/actors', 'Threat actors'],
		['/evolution', 'Actor evolution'],
		['/search', 'Research search'],
		['/technical', 'Technical intelligence']
	] as const) {
		await page.goto(path);
		await expect(page.getByRole('heading', { level: 1, name: heading })).toBeVisible();
	}
});

test('operates the private integration register without exposing server credentials', async ({
	page
}) => {
	let adminPostOrigin: string | undefined;
	page.on('request', (request) => {
		if (request.method() === 'POST' && request.url().includes('/admin/integrations')) {
			adminPostOrigin = request.headers().origin;
		}
	});
	for (const width of [320, 768, 1440]) {
		await page.setViewportSize({ width, height: 1000 });
		await page.goto('/admin/integrations');
		await expect(
			page.getByRole('heading', { level: 1, name: 'Intelligence sources' })
		).toBeVisible();
		await expect(page.getByRole('link', { name: 'Admin integrations' })).toBeVisible();
		await expect(page.getByRole('heading', { name: 'MITRE ATT&CK Enterprise' })).toBeVisible();
		await expect(page.getByRole('heading', { name: 'MISP Galaxy' })).toBeVisible();
		await expect(page.getByRole('heading', { name: 'Basic GeoIP and ASN' })).toBeVisible();
		await expect(page.getByText('WATCHTOWER_MALPEDIA_API_KEY')).toBeVisible();
		await expect(page.getByText('PLANNED').first()).toBeVisible();
		expect(await page.getByText(/Twitter|AlienVault OTX/i).count()).toBe(0);
		expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(
			true
		);
		const results = await new AxeBuilder({ page }).analyze();
		expect(results.violations, `${width}px integration accessibility violations`).toEqual([]);
	}

	await page.getByRole('button', { name: 'Queue ATT&CK refresh' }).click();
	expect(adminPostOrigin).toBe(new URL(page.url()).origin);
	await expect(page.getByText('MITRE ATT&CK refresh queued.')).toBeVisible();
	await expect(page.getByText('QUEUED ·')).toBeVisible();
	const html = await page.content();
	expect(html).not.toContain('task-35-browser-operator-token');
	expect(html).not.toContain('X-WATCHTOWER-Operator-Token');
	expect(html).not.toContain('/api/v1/operations/integrations');
});

test('reads current and historic living intelligence with ordered updates', async ({ page }) => {
	await page.goto('/advisories');
	await page.getByRole('link', { name: 'Credential access activity evolves' }).click();
	await expect(page).toHaveURL(/\/advisories\/credential-access-evolution$/);
	await expect(
		page.getByRole('heading', { level: 1, name: 'Credential access activity evolves' })
	).toBeVisible();
	await expect(page.getByText('OBSERVED').first()).toBeVisible();
	await expect(page.getByText('ASSESSED').first()).toBeVisible();
	await expect(page.getByRole('link', { name: 'Midnight Blizzard' })).toBeVisible();
	await expect(page.getByRole('heading', { name: 'Advisory updates' })).toBeVisible();
	await expect(page.getByText('Detection guidance updated')).toBeVisible();

	await page.getByRole('link', { name: 'Previous · v1' }).click();
	await expect(page.getByText('Archived published revision v1')).toBeVisible();
	await expect(page.getByRole('link', { name: 'Open current revision' })).toBeVisible();
});

test('preserves the research hierarchy at the minimum supported width', async ({ page }) => {
	await page.setViewportSize({ width: 320, height: 720 });
	await page.goto('/search');

	await expect(page.getByRole('heading', { level: 1, name: 'Research search' })).toBeVisible();
	await expect(
		page.getByRole('heading', { level: 2, name: 'Threat actors worth investigating' })
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
	await expect(
		page.getByRole('heading', { level: 2, name: 'midnight', exact: true })
	).toBeVisible();
	await expect(page.locator('.result-list article h2 mark').first()).toHaveText('Midnight');
	await expect(page.locator('.result-list article h2')).toHaveText([
		'Midnight Blizzard',
		'PowerShell'
	]);
	await expect(page.locator('.result-list article .chip').first()).toHaveText('OBSERVED');

	await page.getByRole('button', { name: 'Filters' }).click();
	const dialog = page.getByRole('dialog', { name: 'Filter published intelligence' });
	await expect(dialog).toBeVisible();
	await expect(dialog.getByRole('checkbox', { name: 'indicator' })).toBeFocused();
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

test('discovers actors and resolves indicators and CVEs to actor context', async ({ page }) => {
	await page.goto('/search');
	await expect(page.getByText('RECENTLY OBSERVED')).toBeVisible();
	await expect(page.getByText('ACTIVE IN THE INDEX')).toBeVisible();
	await expect(page.getByRole('link', { name: 'Midnight Blizzard' })).toHaveCount(2);

	await page.goto('/search?q=malicious-update.example');
	await expect(
		page.getByRole('article').getByRole('heading', {
			level: 2,
			name: 'malicious-update.example'
		})
	).toBeVisible();
	await expect(page.locator('.result-list article h2 mark')).toHaveText('malicious-update.example');
	await expect(page.getByText('INDICATOR TYPE')).toBeVisible();
	await expect(page.getByText('RELATED THREAT ACTORS')).toBeVisible();
	await expect(
		page.getByText('Published adversary identity with source-linked evolution.')
	).toBeVisible();

	await page.goto('/search?q=CVE-2026-45123');
	await expect(page.locator('.result-list article h2 mark')).toHaveText('CVE-2026-45123');
	await expect(page.getByText('critical / CVSS 9.8')).toBeVisible();
	await expect(page.getByRole('link', { name: 'Midnight Blizzard' })).toBeVisible();
});

test('shows local validation, no-match and safe API error states', async ({ page }) => {
	await page.goto('/search?q=x');
	await expect(page.getByRole('heading', { name: 'Correct the query scope' })).toBeVisible();
	await expect(page.getByText('Enter at least two non-whitespace characters.')).toBeVisible();

	await page.goto('/search?q=nothing');
	await expect(page.getByText('No published matches for nothing')).toBeVisible();

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
		await expect(
			page.getByRole('heading', { level: 2, name: 'midnight', exact: true })
		).toBeVisible();
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

test('public home and advisory detail are accessible and responsive at review widths', async ({
	page
}) => {
	for (const width of [320, 768, 1440]) {
		await page.setViewportSize({ width, height: 900 });
		for (const path of ['/', '/advisories/credential-access-evolution']) {
			await page.goto(path);
			await page.waitForLoadState('networkidle');
			expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(
				true
			);
			const results = await new AxeBuilder({ page }).analyze();
			expect(results.violations, `${width}px ${path} accessibility violations`).toEqual([]);
		}
	}
});
