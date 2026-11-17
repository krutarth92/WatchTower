import { describe, expect, it, vi } from 'vitest';
import type {
	AdvisoryCollectionResponse,
	AdvisoryResponse,
	RevisionRead,
	UpdateCollectionResponse
} from '#lib/api/contracts.ts';
import { loadAdvisoryDetail, loadAdvisoryList } from './page.ts';

const revision: RevisionRead = {
	id: '10000000-0000-4000-8000-000000000001',
	version: 2,
	title: 'Published advisory',
	summary: 'Summary',
	created_by: 'analyst',
	created_at: '2026-10-22T00:00:00Z',
	published_at: '2026-10-23T00:00:00Z',
	published_by: 'publisher',
	sections: [],
	evidence: [],
	actors: [],
	campaigns: [],
	techniques: []
};

const detail = {
	data: {
		id: '20000000-0000-4000-8000-000000000001',
		slug: 'published-advisory',
		status: 'published',
		published_revision: 2,
		published_at: '2026-10-23T00:00:00Z',
		created_at: '2026-10-22T00:00:00Z',
		updated_at: '2026-10-23T00:00:00Z',
		revision,
		updates: []
	}
} satisfies AdvisoryResponse;

describe('advisory page loaders', () => {
	it('keeps an empty published list distinct from failure', async () => {
		const response = { data: [], limit: 25 } satisfies AdvisoryCollectionResponse;
		const client = { get: vi.fn(async () => response) };
		expect((await loadAdvisoryList(client)).view).toBe('empty');
	});

	it('rejects malformed slugs without calling the backend', async () => {
		const client = { get: vi.fn() };
		const result = await loadAdvisoryDetail('../draft', null, client);
		expect(result.view).toBe('unavailable');
		expect(result.error?.status).toBe(404);
		expect(client.get).not.toHaveBeenCalled();
	});

	it('retains the advisory when its update stream fails', async () => {
		const client = {
			get: vi.fn(async (path: string) => {
				if (path.endsWith('/updates')) throw new Error('offline');
				return detail;
			})
		};
		const result = await loadAdvisoryDetail('published-advisory', null, client);
		expect(result.view).toBe('success');
		expect(result.response).toEqual(detail);
		expect(result.updatesError?.message).toContain('temporarily unavailable');
	});

	it('loads historic revisions without mixing in current updates', async () => {
		const updates = { data: [], after_sequence: 0, limit: 25 } satisfies UpdateCollectionResponse;
		const client = { get: vi.fn(async () => detail) };
		const result = await loadAdvisoryDetail('published-advisory', 1, client);
		expect(result.archivedVersion).toBe(1);
		expect(result.updates).toBeNull();
		expect(client.get).toHaveBeenCalledTimes(1);
		expect(updates.limit).toBe(25);
	});
});
