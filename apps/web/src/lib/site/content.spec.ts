import { describe, expect, it } from 'vitest';
import { latestPlatformUpdate, platformUpdates, primaryNavigation } from './content.ts';

describe('public site content', () => {
	it('defines the six owner-directed modules with unique destinations', () => {
		expect(primaryNavigation.map((item) => item.label)).toEqual([
			'Home',
			'Intelligence',
			'Actors',
			'Evolution',
			'Research',
			'Technical'
		]);
		expect(new Set(primaryNavigation.map((item) => item.href)).size).toBe(6);
	});

	it('uses the same newest release for the rail and archive', () => {
		expect(latestPlatformUpdate).toBe(platformUpdates[0]);
		expect(platformUpdates.every((update) => update.href.startsWith('/'))).toBe(true);
	});
});
