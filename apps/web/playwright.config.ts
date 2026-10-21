import { defineConfig } from '@playwright/test';

export default defineConfig({
	use: { baseURL: process.env.WATCHTOWER_E2E_BASE_URL ?? 'http://127.0.0.1:4173' },
	testMatch: '**/*.e2e.{ts,js}'
});
