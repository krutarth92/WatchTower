import { render, screen } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';
import type { TimelineEvent } from '#lib/api/contracts.ts';
import ActorTimelineEvent from './ActorTimelineEvent.svelte';

const source = {
	id: '10000000-0000-4000-8000-000000000001',
	name: 'Published source',
	kind: 'fixture',
	base_url: null
};

const event: TimelineEvent = {
	id: '20000000-0000-4000-8000-000000000002',
	event_type: 'observation',
	source_native_id: 'native-7',
	title: '<img src=x onerror=alert(1)>',
	summary: '<script>alert("unsafe")</script>',
	observed_at: '2026-03-10T10:00:00Z',
	first_seen: null,
	last_seen: null,
	confidence: 75,
	intelligence_type: 'observed',
	origin: 'imported',
	raw_evidence_id: null,
	source,
	evidence: [
		{
			id: '30000000-0000-4000-8000-000000000001',
			citation: 'Hostile locator remains inert',
			excerpt: '<iframe src="https://evil.test"></iframe>',
			locator: 'javascript:alert(1)',
			captured_at: null,
			confidence: null,
			origin: 'imported',
			raw_evidence_id: null,
			source
		}
	],
	behaviors: [],
	techniques: [],
	evidence_truncated: true,
	behaviors_truncated: true,
	techniques_truncated: true
};

describe('ActorTimelineEvent', () => {
	it('keeps hostile content inert and surfaces uncertainty and truncation', () => {
		const { container } = render(ActorTimelineEvent, { event });
		expect(screen.getByText('<img src=x onerror=alert(1)>')).toBeTruthy();
		expect(screen.getByText('<script>alert("unsafe")</script>')).toBeTruthy();
		expect(container.querySelector('script, img, iframe')).toBeNull();
		expect(screen.getAllByText('Not established')).toHaveLength(2);
		expect(screen.getByText('Additional evidence is available through the API.')).toBeTruthy();
		expect(screen.getByText('javascript:alert(1)')).toBeTruthy();
		expect(container.querySelector('a')).toBeNull();
	});
});
