import { fireEvent, render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import EvidenceDisclosure from './EvidenceDisclosure.svelte';
import StatePanel from './StatePanel.svelte';
import StatusChip from './StatusChip.svelte';
import UtcDate from './UtcDate.svelte';

const evidence = {
	id: '20000000-0000-4000-8000-000000000001',
	citation: 'Fixture citation',
	excerpt: '<script>alert("unsafe")</script>',
	locator: 'javascript:alert(1)',
	captured_at: '2026-01-02T03:04:05Z',
	confidence: 86,
	origin: 'imported' as const,
	raw_evidence_id: null,
	source: {
		id: '10000000-0000-4000-8000-000000000001',
		name: 'Fixture source',
		kind: 'fixture',
		base_url: null
	}
};

describe('shared intelligence components', () => {
	it.each([
		['OBSERVED', 'observed'],
		['ASSESSED', 'assessed'],
		['CRITICAL', 'critical']
	] as const)('renders the %s label as text', (label, tone) => {
		render(StatusChip, { label, tone });
		expect(screen.getByText(label)).toBeTruthy();
	});

	it('keeps hostile evidence text inert and rejects unsafe locator links', () => {
		const { container } = render(EvidenceDisclosure, { evidence });
		expect(screen.getByText('<script>alert("unsafe")</script>')).toBeTruthy();
		expect(container.querySelector('script')).toBeNull();
		expect(container.querySelector('a')).toBeNull();
		expect(screen.getByText('javascript:alert(1)')).toBeTruthy();
	});

	it('renders loading, empty and retryable error states', async () => {
		const retry = vi.fn();
		const { rerender } = render(StatePanel, {
			state: 'loading',
			title: 'Loading intelligence',
			message: 'Please wait.'
		});
		expect(screen.getByText('Loading intelligence')).toBeTruthy();

		await rerender({ state: 'empty', title: 'No matches', message: 'Try another scope.' });
		expect(screen.getByText('No matches')).toBeTruthy();

		await rerender({
			state: 'error',
			title: 'Panel unavailable',
			message: 'Try again.',
			requestId: 'request-123',
			onRetry: retry
		});
		await fireEvent.click(screen.getByRole('button', { name: 'Retry' }));
		expect(retry).toHaveBeenCalledOnce();
		expect(screen.getByText(/request-123/)).toBeTruthy();
	});

	it('exposes the UTC value through a time element', () => {
		const { container } = render(UtcDate, { value: '2026-01-02T03:04:05Z' });
		const time = container.querySelector('time');
		expect(time?.getAttribute('datetime')).toBe('2026-01-02T03:04:05.000Z');
		expect(time?.getAttribute('title')).toContain('UTC');
	});
});
