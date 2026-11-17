import { loadAdvisoryDetail } from '#lib/server/advisories/page.ts';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = ({ params }) =>
	loadAdvisoryDetail(params.slug, Number(params.version));
