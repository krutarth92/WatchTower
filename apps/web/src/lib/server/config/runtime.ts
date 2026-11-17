import { parseApiOrigin, privateBoolean, privateEnvironmentLabel } from './api-origin';

const operatorToken = process.env.WATCHTOWER_OPERATOR_TOKEN?.trim() || null;
const adminRequested = privateBoolean(
	'WATCHTOWER_ADMIN_ENABLED',
	process.env.WATCHTOWER_ADMIN_ENABLED
);

export const runtimeConfig = Object.freeze({
	apiOrigin: parseApiOrigin(process.env.WATCHTOWER_API_ORIGIN),
	environmentLabel: privateEnvironmentLabel(process.env.WATCHTOWER_UI_ENVIRONMENT),
	operatorToken,
	adminEnabled: adminRequested && operatorToken !== null
});
