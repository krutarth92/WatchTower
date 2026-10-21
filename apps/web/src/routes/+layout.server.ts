import { runtimeConfig } from '#lib/server/config/runtime.ts';
import type { LayoutServerLoad } from './$types';

export const load: LayoutServerLoad = ({ url }) => ({
	environmentLabel: runtimeConfig.environmentLabel,
	currentPath: url.pathname
});
