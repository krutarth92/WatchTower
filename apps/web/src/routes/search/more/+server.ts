import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import type { SearchResponse } from '#lib/api/contracts.ts';
import { PublicApiError, publicApi } from '#lib/server/api/client.ts';
import { backendSearchQuery, parseSearchState } from '#lib/search/state.ts';

const maxCursorLength = 4096;

export const POST: RequestHandler = async ({ request, url }) => {
	const search = parseSearchState(url.searchParams);
	if (!search.submitted || search.errors.length) {
		return json(
			{ error: { message: 'The search filters are invalid.', requestId: null } },
			{ status: 422 }
		);
	}

	let cursor: unknown;
	try {
		cursor = ((await request.json()) as { cursor?: unknown }).cursor;
	} catch {
		cursor = null;
	}
	if (typeof cursor !== 'string' || !cursor || cursor.length > maxCursorLength) {
		return json(
			{ error: { message: 'The result cursor is invalid.', requestId: null } },
			{ status: 422 }
		);
	}

	try {
		const response = await publicApi.get<SearchResponse>(
			'/api/v1/search',
			backendSearchQuery(search.state, cursor)
		);
		return json(response, { headers: { 'Cache-Control': 'no-store' } });
	} catch (caught) {
		const detail = caught instanceof PublicApiError ? caught.detail : null;
		const status = detail?.status === 429 ? 429 : detail?.status === 422 ? 422 : 503;
		const message =
			status === 429
				? 'Search is temporarily rate limited. Wait a moment and try again.'
				: status === 422
					? 'The result cursor no longer matches this search.'
					: 'More published intelligence could not be loaded.';
		return json(
			{ error: { message, requestId: detail?.requestId ?? null } },
			{ status, headers: { 'Cache-Control': 'no-store' } }
		);
	}
};
