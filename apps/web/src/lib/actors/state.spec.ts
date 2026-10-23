import { describe, expect, it } from 'vitest';
import {
	actorTimelineQuery,
	parseActorWorkspaceState,
	serializeActorWorkspaceState,
	validActorId
} from './state.ts';

describe('actor workspace state', () => {
	it('normalizes filters and a search return URL deterministically', () => {
		const parsed = parseActorWorkspaceState(
			new URLSearchParams(
				'fromSearch=%2Fsearch%3Fentity_type%3Dactor%26q%3Dmidnight&intelligence_type=observed&date_to=2026-03-31&date_from=2026-01-01'
			)
		);
		expect(parsed.errors).toEqual([]);
		expect(serializeActorWorkspaceState(parsed.state).toString()).toBe(
			'date_from=2026-01-01&date_to=2026-03-31&intelligence_type=observed&fromSearch=%2Fsearch%3Fq%3Dmidnight%26entity_type%3Dactor'
		);
		expect(actorTimelineQuery(parsed.state, 'opaque')).toEqual({
			date_from: '2026-01-01T00:00:00.000Z',
			date_to: '2026-03-31T23:59:59.999Z',
			intelligence_type: 'observed',
			limit: 25,
			cursor: 'opaque'
		});
	});

	it.each([
		'fromSearch=https%3A%2F%2Fevil.test%2Fsearch',
		'fromSearch=%2F%2Fevil.test%2Fsearch',
		'fromSearch=%2Fsearch%3Funknown%3D1',
		'date_from=2026-02-30',
		'date_from=2026-04-01&date_to=2026-03-01',
		'intelligence_type=forecast',
		'cursor=opaque',
		'date_from=2026-01-01&date_from=2026-01-02'
	])('rejects invalid state: %s', (query) => {
		expect(parseActorWorkspaceState(new URLSearchParams(query)).errors.length).toBeGreaterThan(0);
	});

	it('validates canonical actor UUIDs', () => {
		expect(validActorId('20000000-0000-4000-8000-000000000001')).toBe(true);
		expect(validActorId('not-an-actor')).toBe(false);
	});
});
