import { parseApiOrigin, privateEnvironmentLabel } from './api-origin';

export const runtimeConfig = Object.freeze({
	apiOrigin: parseApiOrigin(process.env.WATCHTOWER_API_ORIGIN),
	environmentLabel: privateEnvironmentLabel(process.env.WATCHTOWER_UI_ENVIRONMENT)
});
