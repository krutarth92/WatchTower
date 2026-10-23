import { describe, expect, it } from 'vitest';
import { backendSearchQuery, parseSearchState, serializeSearchState } from './state.ts';

describe('search URL state', () => {
	it('normalizes and serializes supported state deterministically', () => {
		const parsed = parseSearchState(
			new URLSearchParams(
				'q=%20midnight%20%20blizzard%20&entity_type=technique&entity_type=actor&intelligence_type=observed&source_id=10000000-0000-4000-8000-000000000001&date_from=2026-01-01&date_to=2026-01-31'
			)
		);

		expect(parsed.errors).toEqual([]);
		expect(parsed.state.query).toBe('midnight blizzard');
		expect(parsed.state.entityTypes).toEqual(['actor', 'technique']);
		expect(serializeSearchState(parsed.state).toString()).toBe(
			'q=midnight+blizzard&entity_type=actor&entity_type=technique&intelligence_type=observed&source_id=10000000-0000-4000-8000-000000000001&date_from=2026-01-01&date_to=2026-01-31'
		);
	});

	it('rejects malformed filters before transport', () => {
		const parsed = parseSearchState(
			new URLSearchParams(
				'q=x&entity_type=unknown&intelligence_type=guessed&source_id=not-a-uuid&date_from=2026-02-30&date_to=2026-01-01&cursor=secret'
			)
		);

		expect(parsed.errors).toEqual(
			expect.arrayContaining([
				'Unsupported search parameter: cursor.',
				'Enter at least two non-whitespace characters.',
				'Unsupported entity type: unknown.',
				'Unsupported intelligence type: guessed.',
				'Source ID must be a valid UUID.',
				'Start date must be a valid UTC date.'
			])
		);
	});

	it('keeps the backend cursor opaque and out of public URL serialization', () => {
		const parsed = parseSearchState(new URLSearchParams('q=actor'));
		const query = backendSearchQuery(parsed.state, 'opaque.cursor.value');

		expect(query.cursor).toBe('opaque.cursor.value');
		expect(serializeSearchState(parsed.state).has('cursor')).toBe(false);
		expect(query.limit).toBe(25);
	});
});
