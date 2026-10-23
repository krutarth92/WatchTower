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
	indicator_type: null,
	indicator_value: null,
	severity: null,
	cvss_score: null,
	related_actors: [],
	related_actors_truncated: false,
	match_kind: 'exact',
	score: 100.25
};

describe('search result card', () => {
	it('keeps unlinked results self-contained and hostile text inert', () => {
		const { container } = render(SearchResultCard, {
			result: baseResult,
			fromSearch: '/search?q=unsafe',
			query: 'unsafe'
		});

		expect(screen.getByRole('heading', { level: 2 }).textContent).toBe(
			'<script>unsafe technique</script>'
		);
		expect(container.querySelector('mark')?.textContent).toBe('unsafe');
		expect(screen.getByText('No public detail route')).toBeTruthy();
		expect(screen.getAllByText('OBSERVED')).toHaveLength(2);
		expect(container.querySelector('script')).toBeNull();
		expect(container.querySelector('a')).toBeNull();
	});

	it('links actor-associated records and preserves search context', () => {
		render(SearchResultCard, {
			result: { ...baseResult, actor_id: '30000000-0000-4000-8000-000000000001' },
			fromSearch: '/search?q=midnight&entity_type=technique',
			query: 'unsafe'
		});

		const link = screen.getByRole('link', { name: '<script>unsafe technique</script>' });
		expect(link.getAttribute('href')).toBe(
			'/actors/30000000-0000-4000-8000-000000000001?fromSearch=%2Fsearch%3Fq%3Dmidnight%26entity_type%3Dtechnique'
		);
	});

	it('shows related actor detail and links from indicator results', () => {
		render(SearchResultCard, {
			result: {
				...baseResult,
				entity_type: 'indicator',
				title: 'malicious-update.example',
				indicator_type: 'domain',
				indicator_value: 'malicious-update.example',
				related_actors: [
					{
						id: '30000000-0000-4000-8000-000000000001',
						canonical_name: 'Sandworm Team',
						description: 'Disruptive operations actor.',
						latest_observed_at: '2026-10-20T14:00:00Z'
					}
				]
			},
			fromSearch: '/search?q=malicious-update.example',
			query: 'malicious-update.example'
		});

		expect(screen.getByText('Disruptive operations actor.')).toBeTruthy();
		expect(
			screen.getByRole('link', { name: /Open related actor context/ }).getAttribute('href')
		).toBe(
			'/actors/30000000-0000-4000-8000-000000000001?fromSearch=%2Fsearch%3Fq%3Dmalicious-update.example'
		);
	});
});
