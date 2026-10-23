import { loadSearchPage } from '#lib/server/search/page.ts';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ url, setHeaders }) => {
	setHeaders({ 'Cache-Control': 'no-store' });
	return loadSearchPage(url.searchParams);
};
