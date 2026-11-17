import type { ActorDiscoveryResponse } from '#lib/api/contracts.ts';
import { PublicApiError, publicApi } from '#lib/server/api/client.ts';

export interface DiscoveryPageData {
	discovery: ActorDiscoveryResponse | null;
	error: { message: string; requestId: string | null } | null;
}

export async function loadActorDiscovery(limit = 12): Promise<DiscoveryPageData> {
	try {
		return {
			discovery: await publicApi.get<ActorDiscoveryResponse>('/api/v1/search/discovery', { limit }),
			error: null
		};
	} catch (caught) {
		const detail = caught instanceof PublicApiError ? caught.detail : null;
		return {
			discovery: null,
			error: {
				message: 'Published actor discovery is temporarily unavailable.',
				requestId: detail?.requestId ?? null
			}
		};
	}
}
