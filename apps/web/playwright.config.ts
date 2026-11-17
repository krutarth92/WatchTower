import { defineConfig } from '@playwright/test';

export default defineConfig({
	use: {
		baseURL: process.env.WATCHTOWER_E2E_BASE_URL ?? 'http://127.0.0.1:4173',
		extraHTTPHeaders: process.env.WATCHTOWER_E2E_FORWARDED_PROTO
			? { 'x-forwarded-proto': process.env.WATCHTOWER_E2E_FORWARDED_PROTO }
			: undefined
	},
	testMatch: '**/*.e2e.{ts,js}'
});
