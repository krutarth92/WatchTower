import type {
	AdvisoryCollectionResponse,
	AdvisoryResponse,
	UpdateCollectionResponse
} from '#lib/api/contracts.ts';
import { PublicApiError, publicApi } from '#lib/server/api/client.ts';

const slugPattern = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

export interface AdvisoryPageError {
	status: number;
	message: string;
	requestId: string | null;
}

export interface AdvisoryListPageData {
	view: 'success' | 'empty' | 'unavailable';
	response: AdvisoryCollectionResponse | null;
	error: AdvisoryPageError | null;
}

export interface AdvisoryDetailPageData {
	view: 'success' | 'unavailable';
	response: AdvisoryResponse | null;
	updates: UpdateCollectionResponse | null;
	updatesError: AdvisoryPageError | null;
	error: AdvisoryPageError | null;
	archivedVersion: number | null;
}

interface AdvisoryClient {
	get(
		path: string,
		query?: Readonly<Record<string, string | number | readonly string[] | undefined>>
	): Promise<unknown>;
}

const defaultClient: AdvisoryClient = {
	get: (path, query) => publicApi.get(path, query)
};

function normalizedError(caught: unknown, fallback: string): AdvisoryPageError {
	const detail = caught instanceof PublicApiError ? caught.detail : null;
	return {
		status: detail?.status ?? 0,
		message:
			detail?.status === 404
				? 'This published record is unavailable.'
				: detail?.status === 429
					? 'Published intelligence is temporarily rate limited. Wait a moment and try again.'
					: fallback,
		requestId: detail?.requestId ?? null
	};
}

export async function loadAdvisoryList(
	client: AdvisoryClient = defaultClient
): Promise<AdvisoryListPageData> {
	try {
		const response = (await client.get('/api/v1/advisories', {
			limit: 25
		})) as AdvisoryCollectionResponse;
		return {
			view: response.data.length ? 'success' : 'empty',
			response,
			error: null
		};
	} catch (caught) {
		return {
			view: 'unavailable',
			response: null,
			error: normalizedError(caught, 'Published advisories are temporarily unavailable.')
		};
	}
}

export async function loadAdvisoryDetail(
	slug: string,
	version: number | null = null,
	client: AdvisoryClient = defaultClient
): Promise<AdvisoryDetailPageData> {
	if (
		!slugPattern.test(slug) ||
		(version !== null && (!Number.isSafeInteger(version) || version < 1))
	) {
		return {
			view: 'unavailable',
			response: null,
			updates: null,
			updatesError: null,
			error: { status: 404, message: 'This published record is unavailable.', requestId: null },
			archivedVersion: version
		};
	}

	const path =
		version === null
			? `/api/v1/advisories/${slug}`
			: `/api/v1/advisories/${slug}/revisions/${version}`;

	try {
		const response = (await client.get(path)) as AdvisoryResponse;
		if (version !== null) {
			return {
				view: 'success',
				response,
				updates: null,
				updatesError: null,
				error: null,
				archivedVersion: version
			};
		}

		try {
			const updates = (await client.get(`/api/v1/advisories/${slug}/updates`, {
				after_sequence: 0,
				limit: 25
			})) as UpdateCollectionResponse;
			return {
				view: 'success',
				response,
				updates,
				updatesError: null,
				error: null,
				archivedVersion: null
			};
		} catch (caught) {
			return {
				view: 'success',
				response,
				updates: null,
				updatesError: normalizedError(caught, 'Advisory updates are temporarily unavailable.'),
				error: null,
				archivedVersion: null
			};
		}
	} catch (caught) {
		return {
			view: 'unavailable',
			response: null,
			updates: null,
			updatesError: null,
			error: normalizedError(caught, 'The published advisory is temporarily unavailable.'),
			archivedVersion: version
		};
	}
}

export function validAdvisorySlug(slug: string): boolean {
	return slugPattern.test(slug);
}
