import type { ApiErrorResponse, SearchResponse, TimelinePageResponse } from '#lib/api/contracts.ts';

const source = {
	id: '10000000-0000-4000-8000-000000000001',
	name: 'Published source',
	kind: 'fixture',
	base_url: 'https://example.test'
} as const;

export const searchSuccessFixture = {
	query: 'sample actor',
	data: [
		{
			entity_type: 'actor',
			id: '20000000-0000-4000-8000-000000000001',
			title: 'Sample actor',
			summary: 'Representative published fixture data.',
			source_id: source.id,
			actor_id: '20000000-0000-4000-8000-000000000001',
			external_id: null,
			observed_at: '2026-01-02T03:04:05Z',
			intelligence_type: 'observed',
			origin: 'imported',
			indicator_type: null,
			indicator_value: null,
			severity: null,
			cvss_score: null,
			related_actors: [],
			related_actors_truncated: false,
			match_kind: 'exact',
			score: 1
		}
	],
	limit: 25,
	next_cursor: null
} satisfies SearchResponse;

export const searchEmptyFixture = {
	query: 'no published match',
	data: [],
	limit: 25,
	next_cursor: null
} satisfies SearchResponse;

export const timelineTruncatedFixture = {
	data: [],
	page: { limit: 25, next_cursor: 'opaque-next-page' }
} satisfies TimelinePageResponse;

export const partialPanelFixture = {
	identity: { state: 'success' as const },
	timeline: { state: 'error' as const, requestId: 'fixture-request-id' }
};

export const stableApiErrorFixture = {
	error: {
		code: 'validation_error',
		message: 'The request parameters are invalid.',
		request_id: 'fixture-request-id',
		details: [{ location: 'query.q', message: 'Value is too short.', type: 'string_too_short' }]
	}
} satisfies ApiErrorResponse;
