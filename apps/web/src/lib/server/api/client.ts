import { runtimeConfig } from '#lib/server/config/runtime.ts';
import type { ApiErrorDetail, ApiErrorResponse } from '#lib/api/contracts.ts';

const timeoutMs = 10_000;
const uuidPath =
	'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-8][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}';
const slugPath = '[a-z0-9]+(?:-[a-z0-9]+)*';

const routes = [
	{
		pattern: /^\/api\/v1\/search$/,
		query: new Set([
			'q',
			'entity_type',
			'source_id',
			'intelligence_type',
			'date_from',
			'date_to',
			'limit',
			'cursor'
		])
	},
	{ pattern: /^\/api\/v1\/actors\/search$/, query: new Set(['q']) },
	{ pattern: new RegExp(`^/api/v1/actors/${uuidPath}$`), query: new Set<string>() },
	{
		pattern: new RegExp(`^/api/v1/actors/${uuidPath}/(?:aliases|associations|references)$`),
		query: new Set<string>()
	},
	{
		pattern: new RegExp(`^/api/v1/actors/${uuidPath}/(?:observations|timeline)$`),
		query: new Set(['limit', 'cursor', 'date_from', 'date_to', 'intelligence_type'])
	},
	{ pattern: /^\/api\/v1\/advisories$/, query: new Set(['limit']) },
	{ pattern: new RegExp(`^/api/v1/advisories/${slugPath}$`), query: new Set<string>() },
	{
		pattern: new RegExp(`^/api/v1/advisories/${slugPath}/revisions/[1-9][0-9]*$`),
		query: new Set<string>()
	},
	{
		pattern: new RegExp(`^/api/v1/advisories/${slugPath}/updates$`),
		query: new Set(['after_sequence', 'limit'])
	}
] as const;

export type QueryValue = string | number | readonly string[] | undefined;
export type PublicQuery = Readonly<Record<string, QueryValue>>;

export interface NormalizedApiError {
	status: number;
	code: string;
	message: string;
	requestId: string | null;
	details: ApiErrorDetail[];
}

export class PublicApiError extends Error {
	readonly detail: NormalizedApiError;

	constructor(detail: NormalizedApiError) {
		super(detail.message);
		this.name = 'PublicApiError';
		this.detail = detail;
	}
}

export interface PublicApiClientOptions {
	fetch?: typeof globalThis.fetch;
	origin?: string;
	timeout?: number;
}

function allowedRoute(path: string) {
	return routes.find((route) => route.pattern.test(path));
}

function requestUrl(origin: string, path: string, query: PublicQuery): URL {
	const route = allowedRoute(path);
	if (!route) throw new TypeError('The API path is not an allowlisted public-read route.');

	const url = new URL(path, `${origin}/`);
	for (const [key, value] of Object.entries(query)) {
		if (!route.query.has(key)) throw new TypeError(`The query key '${key}' is not allowed.`);
		if (value === undefined) continue;
		for (const item of Array.isArray(value) ? value : [value]) {
			url.searchParams.append(key, String(item));
		}
	}
	return url;
}

function genericError(status: number, requestId: string | null): NormalizedApiError {
	return {
		status,
		code: status === 0 ? 'api_unavailable' : 'unexpected_response',
		message:
			status === 0
				? 'The WATCHTOWER API is unavailable. Check the local backend and try again.'
				: 'The request could not be completed.',
		requestId,
		details: []
	};
}

function isApiErrorResponse(value: unknown): value is ApiErrorResponse {
	if (!value || typeof value !== 'object' || !('error' in value)) return false;
	const error = (value as { error?: unknown }).error;
	return Boolean(
		error &&
		typeof error === 'object' &&
		'code' in error &&
		typeof error.code === 'string' &&
		'message' in error &&
		typeof error.message === 'string' &&
		'request_id' in error &&
		typeof error.request_id === 'string'
	);
}

function safeDetails(value: unknown): ApiErrorDetail[] {
	if (!Array.isArray(value)) return [];
	return value.filter((detail): detail is ApiErrorDetail =>
		Boolean(
			detail &&
			typeof detail === 'object' &&
			'location' in detail &&
			typeof detail.location === 'string' &&
			'message' in detail &&
			typeof detail.message === 'string' &&
			'type' in detail &&
			typeof detail.type === 'string'
		)
	);
}

async function normalizeResponseError(response: Response): Promise<NormalizedApiError> {
	const headerRequestId = response.headers.get('x-request-id');
	try {
		const body: unknown = await response.json();
		if (isApiErrorResponse(body)) {
			return {
				status: response.status,
				code: body.error.code,
				message: body.error.message,
				requestId: body.error.request_id || headerRequestId,
				details: safeDetails(body.error.details)
			};
		}
	} catch {
		// The response is untrusted and may not contain JSON.
	}
	return genericError(response.status, headerRequestId);
}

function combinedSignal(parent: AbortSignal | undefined, timeout: number): AbortSignal {
	const timeoutSignal = AbortSignal.timeout(timeout);
	return parent ? AbortSignal.any([parent, timeoutSignal]) : timeoutSignal;
}

export function createPublicApiClient(options: PublicApiClientOptions = {}) {
	const fetcher = options.fetch ?? globalThis.fetch;
	const origin = options.origin ?? runtimeConfig.apiOrigin;
	const requestTimeout = options.timeout ?? timeoutMs;

	return Object.freeze({
		async get<T>(path: string, query: PublicQuery = {}, signal?: AbortSignal): Promise<T> {
			const url = requestUrl(origin, path, query);
			let networkAttempt = 0;

			while (true) {
				try {
					const response = await fetcher(url, {
						method: 'GET',
						headers: { Accept: 'application/json', 'X-Request-ID': crypto.randomUUID() },
						signal: combinedSignal(signal, requestTimeout)
					});
					if (!response.ok) throw new PublicApiError(await normalizeResponseError(response));
					return (await response.json()) as T;
				} catch (error) {
					if (error instanceof PublicApiError) throw error;
					if (signal?.aborted) {
						throw new PublicApiError({
							...genericError(0, null),
							code: 'request_cancelled',
							message: 'The request was cancelled.'
						});
					}
					if (error instanceof DOMException && error.name === 'TimeoutError') {
						throw new PublicApiError({ ...genericError(0, null), code: 'api_timeout' });
					}
					if (networkAttempt === 0) {
						networkAttempt += 1;
						continue;
					}
					throw new PublicApiError(genericError(0, null));
				}
			}
		}
	});
}

export const publicApi = createPublicApiClient();
