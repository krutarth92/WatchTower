import { expect, test } from '@playwright/test';

test('redirects to the research shell', async ({ page }) => {
	await page.goto('/');

	await expect(page).toHaveURL(/\/search$/);
	await expect(page.getByRole('heading', { level: 1, name: /Track adversaries/ })).toBeVisible();
	await expect(page.getByText('LOCAL / PRIVATE')).toBeVisible();
});
