const DEFAULT_API_ORIGIN = 'http://127.0.0.1:8000';
const ALLOWED_PROTOCOLS = new Set(['http:', 'https:']);

export function parseApiOrigin(value: string | undefined): string {
	const candidate = value?.trim() || DEFAULT_API_ORIGIN;
	let parsed: URL;

	try {
		parsed = new URL(candidate);
	} catch {
		throw new Error('WATCHTOWER_API_ORIGIN must be an absolute HTTP(S) origin');
	}

	if (!ALLOWED_PROTOCOLS.has(parsed.protocol)) {
		throw new Error('WATCHTOWER_API_ORIGIN must use HTTP or HTTPS');
	}

	if (parsed.username || parsed.password) {
		throw new Error('WATCHTOWER_API_ORIGIN must not contain credentials');
	}

	if (parsed.pathname !== '/' || parsed.search || parsed.hash) {
		throw new Error('WATCHTOWER_API_ORIGIN must not contain a path, query, or fragment');
	}

	return parsed.origin;
}

export function privateEnvironmentLabel(value: string | undefined): string {
	switch (value?.trim().toLowerCase()) {
		case 'test':
			return 'TEST / PRIVATE';
		case 'staging':
			return 'STAGING / PRIVATE';
		default:
			return 'LOCAL / PRIVATE';
	}
}
