import type { ActorDiscoveryResponse, AdvisoryCollectionResponse } from '#lib/api/contracts.ts';
import { PublicApiError, publicApi } from '#lib/server/api/client.ts';

export interface HomePageData {
	advisories: AdvisoryCollectionResponse | null;
	discovery: ActorDiscoveryResponse | null;
	errors: {
		advisories: string | null;
		discovery: string | null;
	};
}

interface HomeClient {
	get: (
		path: string,
		query: Readonly<Record<string, string | number | readonly string[] | undefined>>
	) => Promise<AdvisoryCollectionResponse | ActorDiscoveryResponse>;
}

const defaultClient: HomeClient = { get: (path, query) => publicApi.get(path, query) };

function message(reason: unknown): string {
	if (reason instanceof PublicApiError && reason.detail.status === 429) {
		return 'This feed is temporarily rate limited.';
	}
	return 'Published data is temporarily unavailable.';
}

export async function loadHomePage(client: HomeClient = defaultClient): Promise<HomePageData> {
	const [advisories, discovery] = await Promise.allSettled([
		client.get('/api/v1/advisories', { limit: 4 }),
		client.get('/api/v1/search/discovery', { limit: 6 })
	]);

	return {
		advisories:
			advisories.status === 'fulfilled' ? (advisories.value as AdvisoryCollectionResponse) : null,
		discovery:
			discovery.status === 'fulfilled' ? (discovery.value as ActorDiscoveryResponse) : null,
		errors: {
			advisories: advisories.status === 'rejected' ? message(advisories.reason) : null,
			discovery: discovery.status === 'rejected' ? message(discovery.reason) : null
		}
	};
}
