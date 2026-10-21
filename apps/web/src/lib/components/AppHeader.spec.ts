import { render, screen } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';
import AppHeader from './AppHeader.svelte';

describe('AppHeader', () => {
	it('exposes the research destination and private environment', () => {
		render(AppHeader, { environmentLabel: 'LOCAL / PRIVATE', currentPath: '/search' });

		expect(
			screen.getByRole('link', { name: 'WATCHTOWER research home' }).getAttribute('href')
		).toBe('/search');
		expect(screen.getByRole('link', { name: 'Research' }).getAttribute('aria-current')).toBe(
			'page'
		);
		expect(screen.getByText('LOCAL / PRIVATE')).toBeTruthy();
	});
});
