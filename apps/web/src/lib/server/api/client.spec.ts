import { describe, expect, it, vi } from 'vitest';
import { PublicApiError, createPublicApiClient } from './client.ts';

const origin = 'http://127.0.0.1:8000';

describe('public API client', () => {
	it('allows only documented public paths and query keys', async () => {
		const fetcher = vi.fn<typeof fetch>(async () => Response.json({ data: [] }));
		const client = createPublicApiClient({ fetch: fetcher, origin });

		await client.get('/api/v1/search', { q: 'actor', entity_type: ['actor', 'alias'] });
		expect(fetcher).toHaveBeenCalledOnce();
		expect(String(fetcher.mock.calls[0]?.[0])).toContain('entity_type=actor&entity_type=alias');
		await expect(client.get('/api/v1/operations/advisories')).rejects.toThrow(/allowlisted/);
		await expect(
			client.get('/api/v1/search', { backend_url: 'https://evil.test' })
		).rejects.toThrow(/query key/);
	});

	it('retries one network failure and sends a fresh request id', async () => {
		const fetcher = vi
			.fn<typeof fetch>()
			.mockRejectedValueOnce(new TypeError('network unavailable'))
			.mockResolvedValueOnce(Response.json({ data: [] }));
		const client = createPublicApiClient({ fetch: fetcher, origin });

		await expect(client.get('/api/v1/advisories')).resolves.toEqual({ data: [] });
		expect(fetcher).toHaveBeenCalledTimes(2);
		const firstHeaders = new Headers(fetcher.mock.calls[0]?.[1]?.headers);
		const secondHeaders = new Headers(fetcher.mock.calls[1]?.[1]?.headers);
		expect(firstHeaders.get('x-request-id')).toMatch(/^[0-9a-f-]{36}$/);
		expect(secondHeaders.get('x-request-id')).not.toBe(firstHeaders.get('x-request-id'));
	});

	it('normalizes API errors without retrying responses', async () => {
		const fetcher = vi.fn(async () =>
			Response.json(
				{
					error: {
						code: 'validation_error',
						message: 'Invalid filter.',
						request_id: 'request-123',
						details: [{ location: 'query.q', message: 'Invalid.', type: 'value_error' }]
					}
				},
				{ status: 422 }
			)
		);
		const client = createPublicApiClient({ fetch: fetcher, origin });

		const error = await client.get('/api/v1/search', { q: 'actor' }).catch((caught) => caught);
		expect(error).toBeInstanceOf(PublicApiError);
		expect((error as PublicApiError).detail).toMatchObject({
			status: 422,
			code: 'validation_error',
			requestId: 'request-123'
		});
		expect(fetcher).toHaveBeenCalledOnce();
	});

	it('uses a generic error for untrusted non-JSON responses', async () => {
		const fetcher = vi.fn(
			async () =>
				new Response('<secret>upstream detail</secret>', {
					status: 500,
					headers: { 'x-request-id': 'request-500' }
				})
		);
		const client = createPublicApiClient({ fetch: fetcher, origin });

		const error = await client.get('/api/v1/advisories').catch((caught) => caught);
		expect((error as PublicApiError).detail).toEqual({
			status: 500,
			code: 'unexpected_response',
			message: 'The request could not be completed.',
			requestId: 'request-500',
			details: []
		});
	});
});
