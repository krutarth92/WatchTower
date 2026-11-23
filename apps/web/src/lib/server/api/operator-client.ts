import { runtimeConfig } from '#lib/server/config/runtime.ts';
import type {
	IntegrationCatalogResponse,
	IntegrationSyncResponse,
	IngestionJobKind
} from '#lib/integrations/contracts.ts';

const timeoutMs = 10_000;
const catalogPath = '/api/v1/operations/integrations';
const syncJobs = {
	'mitre-attack': 'mitre_attack_refresh',
	'misp-galaxy': 'misp_galaxy_refresh',
	cisa: 'cisa_kev_refresh',
	'microsoft-threat-intelligence': 'microsoft_threat_intelligence_refresh',
	'unit-42': 'unit_42_refresh',
	'the-hacker-news': 'the_hacker_news_refresh'
} as const satisfies Record<string, IngestionJobKind>;

export type SyncIntegrationKey = keyof typeof syncJobs;

function syncPath(integrationKey: SyncIntegrationKey) {
	return `/api/v1/operations/integrations/${integrationKey}/sync`;
}

export interface OperatorApiClientOptions {
	fetch?: typeof globalThis.fetch;
	origin?: string;
	token?: string | null;
	timeout?: number;
}

export interface OperatorApiErrorDetail {
	status: number;
	code: string;
	message: string;
	requestId: string | null;
}

export class OperatorApiError extends Error {
	readonly detail: OperatorApiErrorDetail;

	constructor(detail: OperatorApiErrorDetail) {
		super(detail.message);
		this.name = 'OperatorApiError';
		this.detail = detail;
	}
}

function genericError(status: number, requestId: string | null): OperatorApiErrorDetail {
	return {
		status,
		code: status === 0 ? 'operator_api_unavailable' : 'unexpected_response',
		message:
			status === 0
				? 'Integration management is temporarily unavailable.'
				: 'The integration request could not be completed.',
		requestId
	};
}

async function responseError(response: Response): Promise<OperatorApiErrorDetail> {
	const fallback = genericError(response.status, response.headers.get('x-request-id'));
	try {
		const body: unknown = await response.json();
		if (!body || typeof body !== 'object' || !('error' in body)) return fallback;
		const error = (body as { error?: unknown }).error;
		if (!error || typeof error !== 'object') return fallback;
		const candidate = error as Record<string, unknown>;
		return {
			status: response.status,
			code: typeof candidate.code === 'string' ? candidate.code : fallback.code,
			message: typeof candidate.message === 'string' ? candidate.message : fallback.message,
			requestId:
				typeof candidate.request_id === 'string' ? candidate.request_id : fallback.requestId
		};
	} catch {
		return fallback;
	}
}

export function createOperatorApiClient(options: OperatorApiClientOptions = {}) {
	const fetcher = options.fetch ?? globalThis.fetch;
	const origin = options.origin ?? runtimeConfig.apiOrigin;
	const token = 'token' in options ? options.token : runtimeConfig.operatorToken;
	const requestTimeout = options.timeout ?? timeoutMs;

	async function request<T>(path: string, method: 'GET' | 'POST', body?: unknown): Promise<T> {
		if (!token) {
			throw new OperatorApiError({
				status: 503,
				code: 'operator_auth_unavailable',
				message: 'Integration management is not configured.',
				requestId: null
			});
		}
		const allowedSyncPaths = new Set(
			Object.keys(syncJobs).map((key) => syncPath(key as SyncIntegrationKey))
		);
		if (
			(path !== catalogPath || method !== 'GET') &&
			(!allowedSyncPaths.has(path) || method !== 'POST')
		) {
			throw new TypeError('The operator API request is not allowlisted.');
		}

		try {
			const response = await fetcher(new URL(path, `${origin}/`), {
				method,
				headers: {
					Accept: 'application/json',
					'Content-Type': 'application/json',
					'X-Request-ID': crypto.randomUUID(),
					'X-WATCHTOWER-Operator-Token': token
				},
				body: body === undefined ? undefined : JSON.stringify(body),
				signal: AbortSignal.timeout(requestTimeout)
			});
			if (!response.ok) throw new OperatorApiError(await responseError(response));
			return (await response.json()) as T;
		} catch (error) {
			if (error instanceof OperatorApiError) throw error;
			if (error instanceof DOMException && error.name === 'TimeoutError') {
				throw new OperatorApiError({ ...genericError(0, null), code: 'operator_api_timeout' });
			}
			throw new OperatorApiError(genericError(0, null));
		}
	}

	return Object.freeze({
		catalog: () => request<IntegrationCatalogResponse>(catalogPath, 'GET'),
		sync: (integrationKey: SyncIntegrationKey, idempotencyKey: string) =>
			request<IntegrationSyncResponse>(syncPath(integrationKey), 'POST', {
				integration_key: integrationKey,
				job_kind: syncJobs[integrationKey],
				idempotency_key: idempotencyKey
			})
	});
}

export const operatorApi = createOperatorApiClient();
