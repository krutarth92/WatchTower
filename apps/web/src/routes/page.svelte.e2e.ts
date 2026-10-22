import { expect, test } from '@playwright/test';

test('redirects to the research shell', async ({ page }) => {
	await page.goto('/');

	await expect(page).toHaveURL(/\/search$/);
	await expect(page.getByRole('heading', { level: 1, name: /Track adversaries/ })).toBeVisible();
	await expect(page.getByRole('heading', { level: 2, name: 'Foundation telemetry' })).toBeVisible();
	await expect(page.getByText('Private by default')).toBeVisible();
	await expect(page.getByText('LOCAL / PRIVATE')).toBeVisible();
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
