import type { PageServerLoad } from './$types';
import { loadActorPage } from '#lib/server/actors/page.ts';

export const load: PageServerLoad = async ({ params, url, setHeaders }) => {
	setHeaders({ 'Cache-Control': 'no-store' });
	return loadActorPage(params.actorId, url.searchParams);
};
