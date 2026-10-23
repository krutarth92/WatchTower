import { describe, expect, it } from 'vitest';
import { PublicApiError, type NormalizedApiError } from '#lib/server/api/client.ts';
import { loadActorPage, type ActorClient } from './page.ts';

const actorId = '20000000-0000-4000-8000-000000000001';
const apiError = (status: number, requestId = 'request-id') =>
	new PublicApiError({
		status,
		code: status === 404 ? 'not_found' : 'server_error',
		message: 'Internal upstream detail.',
		requestId,
		details: []
	} satisfies NormalizedApiError);

describe('actor page loader', () => {
	it('rejects malformed state before transport', async () => {
		let calls = 0;
		const client: ActorClient = { get: async () => (calls += 1) as never };
		const result = await loadActorPage('bad-id', new URLSearchParams('cursor=secret'), client);
		expect(result.view).toBe('invalid');
		expect(calls).toBe(0);
	});

	it('does not disclose whether a 404 actor is absent or internal', async () => {
		const client: ActorClient = { get: async () => Promise.reject(apiError(404)) };
		const result = await loadActorPage(actorId, new URLSearchParams(), client);
		expect(result.view).toBe('unavailable');
		expect(result.actorError?.message).toBe('This published record is unavailable.');
		expect(result.actorError?.message).not.toContain('Internal upstream detail.');
	});

	it('loads secondary panels independently after identity succeeds', async () => {
		const calls: string[] = [];
		const client: ActorClient = {
			get: async <T>(path: string, query = {}) => {
				calls.push(`${path}?${new URLSearchParams(query as Record<string, string>).toString()}`);
				if (path.endsWith('/aliases')) throw apiError(500, 'alias-request');
				if (path.endsWith('/associations')) {
					return {
						data: {
							behaviors: [],
							techniques: [],
							behaviors_truncated: false,
							techniques_truncated: false
						}
					} as T;
				}
				if (path.endsWith('/timeline')) {
					return { data: [], page: { limit: 25, next_cursor: null } } as T;
				}
				if (path.endsWith('/references')) {
					return {
						data: {
							sources: [],
							evidence: [],
							sources_truncated: false,
							evidence_truncated: false
						}
					} as T;
				}
				return {
					data: { id: actorId, canonical_name: 'Midnight Blizzard', description: null }
				} as T;
			}
		};

		const result = await loadActorPage(
			actorId,
			new URLSearchParams('date_from=2026-01-01&intelligence_type=observed'),
			client
		);
		expect(result.view).toBe('success');
		expect(result.panels.aliases?.state).toBe('error');
		expect(result.panels.associations?.state).toBe('success');
		expect(result.panels.timeline?.state).toBe('success');
		expect(result.panels.references?.state).toBe('success');
		expect(calls[0]).toBe(`/api/v1/actors/${actorId}?`);
		expect(calls.slice(1).map((call) => call.split('?')[0])).toEqual(
			expect.arrayContaining([
				`/api/v1/actors/${actorId}/aliases`,
				`/api/v1/actors/${actorId}/associations`,
				`/api/v1/actors/${actorId}/timeline`,
				`/api/v1/actors/${actorId}/references`
			])
		);
		expect(calls.find((call) => call.includes('/timeline'))).toContain(
			'date_from=2026-01-01T00%3A00%3A00.000Z'
		);
	});
});
