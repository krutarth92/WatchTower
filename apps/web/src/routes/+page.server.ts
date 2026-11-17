import { loadHomePage } from '#lib/server/home/page.ts';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = () => loadHomePage();
