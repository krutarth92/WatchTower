export interface SiteDestination {
	label: string;
	href: string;
	description: string;
	match: (path: string) => boolean;
}

export interface PlatformUpdate {
	id: string;
	publishedAt: string;
	label: string;
	title: string;
	summary: string;
	href: string;
	linkLabel: string;
}

export const primaryNavigation: readonly SiteDestination[] = [
	{
		label: 'Home',
		href: '/',
		description: 'Latest intelligence and significant changes',
		match: (path) => path === '/'
	},
	{
		label: 'Intelligence',
		href: '/advisories',
		description: 'Living articles and advisories',
		match: (path) => path.startsWith('/advisories')
	},
	{
		label: 'Actors',
		href: '/actors',
		description: 'Actor directory and dossiers',
		match: (path) => path === '/actors' || path.startsWith('/actors/')
	},
	{
		label: 'Evolution',
		href: '/evolution',
		description: 'Historical behavior timelines',
		match: (path) => path.startsWith('/evolution')
	},
	{
		label: 'Research',
		href: '/search',
		description: 'Published intelligence search',
		match: (path) => path.startsWith('/search')
	},
	{
		label: 'Technical',
		href: '/technical',
		description: 'ATT&CK, Sigma and STIX context',
		match: (path) => path.startsWith('/technical')
	}
] as const;

export const platformUpdates: readonly PlatformUpdate[] = [
	{
		id: 'indicator-cve-actor-discovery',
		publishedAt: '2026-10-23T00:00:00Z',
		label: 'Search update',
		title: 'Indicators and CVEs now reveal related actors',
		summary:
			'Domain, IP, URL, hash and CVE searches now return bounded actor context with descriptions and latest published activity.',
		href: '/search',
		linkLabel: 'Try intelligence search'
	},
	{
		id: 'actor-research-workspace',
		publishedAt: '2026-10-23T00:00:00Z',
		label: 'Research update',
		title: 'Actor dossiers connect behavior, evolution and evidence',
		summary:
			'Published actor records now combine aliases, techniques, behaviors, a filtered timeline, provenance and evidence in one research flow.',
		href: '/actors',
		linkLabel: 'Browse actors'
	},
	{
		id: 'published-search',
		publishedAt: '2026-10-22T00:00:00Z',
		label: 'Platform update',
		title: 'Published intelligence search is available',
		summary:
			'Deterministic search keeps filters in the URL, preserves backend relevance and limits every result to the published visibility boundary.',
		href: '/search',
		linkLabel: 'Open research'
	}
] as const;

export const latestPlatformUpdate = platformUpdates[0];
