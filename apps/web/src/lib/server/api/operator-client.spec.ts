import { describe, expect, it, vi } from 'vitest';
import { OperatorApiError, createOperatorApiClient } from './operator-client.ts';

describe('operator API client', () => {
	it('adds the server credential to the exact catalog route', async () => {
		const fetcher = vi.fn<typeof fetch>(async () =>
			Response.json({ data: [], enrichment_roadmap: [] })
		);
		const client = createOperatorApiClient({
			fetch: fetcher,
			origin: 'http://127.0.0.1:8000',
			token: 'test-operator-token'
		});

		await expect(client.catalog()).resolves.toEqual({ data: [], enrichment_roadmap: [] });
		const request = fetcher.mock.calls[0];
		expect(String(request?.[0])).toBe('http://127.0.0.1:8000/api/v1/operations/integrations');
		expect(new Headers(request?.[1]?.headers).get('x-watchtower-operator-token')).toBe(
			'test-operator-token'
		);
	});

	it('submits the fixed MITRE action once without retrying', async () => {
		const fetcher = vi.fn<typeof fetch>(async () => {
			throw new TypeError('network unavailable');
		});
		const client = createOperatorApiClient({
			fetch: fetcher,
			origin: 'http://127.0.0.1:8000',
			token: 'test-operator-token'
		});

		const error = await client.syncMitre('key-123').catch((caught) => caught);
		expect(error).toBeInstanceOf(OperatorApiError);
		expect(fetcher).toHaveBeenCalledOnce();
		const request = fetcher.mock.calls[0];
		expect(request?.[1]?.method).toBe('POST');
		expect(JSON.parse(String(request?.[1]?.body))).toEqual({
			integration_key: 'mitre-attack',
			job_kind: 'mitre_attack_refresh',
			idempotency_key: 'key-123'
		});
	});

	it('fails closed when the server credential is absent', async () => {
		const client = createOperatorApiClient({
			fetch: vi.fn<typeof fetch>(),
			origin: 'http://127.0.0.1:8000',
			token: null
		});

		const error = await client.catalog().catch((caught) => caught);
		expect((error as OperatorApiError).detail.code).toBe('operator_auth_unavailable');
	});
});
