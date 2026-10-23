import type { ActorDiscoveryResponse, SearchResponse } from '#lib/api/contracts.ts';
import { PublicApiError, publicApi } from '#lib/server/api/client.ts';
import { backendSearchQuery, parseSearchState } from '#lib/search/state.ts';

export type SearchViewState = 'initial' | 'success' | 'empty' | 'invalid' | 'unavailable';

export interface SearchPageData {
	view: SearchViewState;
	search: ReturnType<typeof parseSearchState>;
	response: SearchResponse | null;
	discovery: ActorDiscoveryResponse | null;
	error: {
		status: number;
		message: string;
		requestId: string | null;
	} | null;
}

interface SearchClient {
	get: (
		path: string,
		query: Readonly<Record<string, string | number | readonly string[] | undefined>>
	) => Promise<SearchResponse | ActorDiscoveryResponse>;
}

const defaultSearchClient: SearchClient = {
	get: (path, query) => publicApi.get(path, query)
};

function unavailableMessage(status: number): string {
	if (status === 429) return 'Search is temporarily rate limited. Wait a moment and try again.';
	return 'Published intelligence search is unavailable. Check the local backend and try again.';
}

export async function loadSearchPage(
	params: URLSearchParams,
	client: SearchClient = defaultSearchClient
): Promise<SearchPageData> {
	const search = parseSearchState(params);
	if (!search.submitted) {
		try {
			const discovery = (await client.get('/api/v1/search/discovery', {
				limit: 12
			})) as ActorDiscoveryResponse;
			return { view: 'initial', search, response: null, discovery, error: null };
		} catch {
			return { view: 'initial', search, response: null, discovery: null, error: null };
		}
	}
	if (search.errors.length) {
		return { view: 'invalid', search, response: null, discovery: null, error: null };
	}

	try {
		const response = (await client.get(
			'/api/v1/search',
			backendSearchQuery(search.state)
		)) as SearchResponse;
		return {
			view: response.data.length ? 'success' : 'empty',
			search,
			response,
			discovery: null,
			error: null
		};
	} catch (caught) {
		const detail = caught instanceof PublicApiError ? caught.detail : null;
		return {
			view: detail?.status === 422 ? 'invalid' : 'unavailable',
			search: detail?.status === 422 ? { ...search, errors: [detail.message] } : search,
			response: null,
			discovery: null,
			error: detail
				? {
						status: detail.status,
						message: unavailableMessage(detail.status),
						requestId: detail.requestId
					}
				: { status: 0, message: unavailableMessage(0), requestId: null }
		};
	}
}
