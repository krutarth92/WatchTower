import { describe, expect, it, vi } from 'vitest';
import type { ActorDiscoveryResponse, AdvisoryCollectionResponse } from '#lib/api/contracts.ts';
import { loadHomePage } from './page.ts';

const advisories = { data: [], limit: 4 } satisfies AdvisoryCollectionResponse;
const discovery = { recent: [], popular: [], limit: 6 } satisfies ActorDiscoveryResponse;

describe('loadHomePage', () => {
	it('retains one successful feed when the other fails', async () => {
		const client = {
			get: vi.fn(async (path: string) => {
				if (path === '/api/v1/advisories') throw new Error('offline');
				return discovery;
			})
		};

		const result = await loadHomePage(client);
		expect(result.advisories).toBeNull();
		expect(result.discovery).toEqual(discovery);
		expect(result.errors.advisories).toContain('temporarily unavailable');
	});

	it('requests bounded published data for both feeds', async () => {
		const client = {
			get: vi.fn(async (path: string) => (path.includes('advisories') ? advisories : discovery))
		};

		await loadHomePage(client);
		expect(client.get).toHaveBeenCalledWith('/api/v1/advisories', { limit: 4 });
		expect(client.get).toHaveBeenCalledWith('/api/v1/search/discovery', { limit: 6 });
	});
});
