import { loadAdvisoryList } from '#lib/server/advisories/page.ts';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = () => loadAdvisoryList();
