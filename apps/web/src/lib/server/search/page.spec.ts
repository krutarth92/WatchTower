import { describe, expect, it, vi } from 'vitest';
import { PublicApiError } from '#lib/server/api/client.ts';
import { loadSearchPage } from './page.ts';

describe('search page loader', () => {
	it('does not call the API for initial or invalid state', async () => {
		const get = vi.fn();

		await expect(loadSearchPage(new URLSearchParams(), { get })).resolves.toMatchObject({
			view: 'initial'
		});
		await expect(loadSearchPage(new URLSearchParams('q=x'), { get })).resolves.toMatchObject({
			view: 'invalid'
		});
		expect(get).not.toHaveBeenCalled();
	});

	it('passes normalized filters and preserves API result order', async () => {
		const record = (id: string, title: string) => ({
			entity_type: 'observation' as const,
			id,
			title,
			summary: null,
			source_id: null,
			actor_id: null,
			external_id: null,
			observed_at: null,
			intelligence_type: 'observed' as const,
			origin: 'imported' as const,
			match_kind: 'full_text' as const,
			score: 0.5
		});
		const response = {
			query: 'midnight',
			data: [record('second-by-title', 'Zulu'), record('first-by-title', 'Alpha')],
			limit: 25,
			next_cursor: 'opaque-next'
		};
		const get = vi.fn(async () => response);

		const result = await loadSearchPage(
			new URLSearchParams('q=midnight&entity_type=observation&date_from=2026-01-01'),
			{ get }
		);

		expect(result.response?.data.map((item) => item.id)).toEqual([
			'second-by-title',
			'first-by-title'
		]);
		expect(get).toHaveBeenCalledWith(
			'/api/v1/search',
			expect.objectContaining({
				q: 'midnight',
				entity_type: ['observation'],
				date_from: '2026-01-01T00:00:00.000Z',
				limit: 25
			})
		);
	});

	it.each([
		[429, 'rate limited'],
		[500, 'unavailable'],
		[0, 'unavailable']
	])('maps status %s to a safe unavailable state', async (status, message) => {
		const get = vi.fn(async () => {
			throw new PublicApiError({
				status,
				code: 'fixture_error',
				message: '<unsafe upstream detail>',
				requestId: 'request-safe',
				details: []
			});
		});

		const result = await loadSearchPage(new URLSearchParams('q=midnight'), { get });

		expect(result.view).toBe('unavailable');
		expect(result.error?.message).toContain(message);
		expect(result.error?.message).not.toContain('unsafe');
		expect(result.error?.requestId).toBe('request-safe');
	});
});
