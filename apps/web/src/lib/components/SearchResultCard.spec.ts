import { render, screen } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';
import type { SearchResultRead } from '#lib/api/contracts.ts';
import SearchResultCard from './SearchResultCard.svelte';

const baseResult: SearchResultRead = {
	entity_type: 'technique',
	id: '20000000-0000-4000-8000-000000000001',
	title: '<script>unsafe technique</script>',
	summary: 'Source-supplied summary remains plain text.',
	source_id: '10000000-0000-4000-8000-000000000001',
	actor_id: null,
	external_id: 'T1059.001',
	observed_at: '2026-01-02T03:04:05Z',
	intelligence_type: 'observed',
	origin: 'imported',
	match_kind: 'exact',
	score: 100.25
};

describe('search result card', () => {
	it('keeps unlinked results self-contained and hostile text inert', () => {
		const { container } = render(SearchResultCard, {
			result: baseResult,
			fromSearch: '/search?q=unsafe'
		});

		expect(screen.getByText('<script>unsafe technique</script>')).toBeTruthy();
		expect(screen.getByText('No public detail route')).toBeTruthy();
		expect(screen.getAllByText('OBSERVED')).toHaveLength(2);
		expect(container.querySelector('script')).toBeNull();
		expect(container.querySelector('a')).toBeNull();
	});

	it('links actor-associated records and preserves search context', () => {
		render(SearchResultCard, {
			result: { ...baseResult, actor_id: '30000000-0000-4000-8000-000000000001' },
			fromSearch: '/search?q=midnight&entity_type=technique'
		});

		const link = screen.getByRole('link', { name: '<script>unsafe technique</script>' });
		expect(link.getAttribute('href')).toBe(
			'/actors/30000000-0000-4000-8000-000000000001?fromSearch=%2Fsearch%3Fq%3Dmidnight%26entity_type%3Dtechnique'
		);
	});
});
