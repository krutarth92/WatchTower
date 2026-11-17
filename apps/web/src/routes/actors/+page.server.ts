import { loadActorDiscovery } from '#lib/server/discovery/page.ts';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = () => loadActorDiscovery(12);
