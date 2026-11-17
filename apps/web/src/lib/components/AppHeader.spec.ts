import { render, screen } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';
import AppHeader from './AppHeader.svelte';

describe('AppHeader', () => {
	it('exposes the public module navigation and current destination', () => {
		render(AppHeader, { environmentLabel: 'LOCAL / PRIVATE', currentPath: '/search' });

		expect(screen.getByRole('link', { name: 'WATCHTOWER home' }).getAttribute('href')).toBe('/');
		expect(screen.getByRole('link', { name: 'Research' }).getAttribute('aria-current')).toBe(
			'page'
		);
		for (const label of ['Home', 'Intelligence', 'Actors', 'Evolution', 'Technical']) {
			expect(screen.getByRole('link', { name: label })).toBeTruthy();
		}
		expect(screen.getByRole('link', { name: 'Platform updates' })).toBeTruthy();
		expect(screen.getByText('LOCAL / PRIVATE')).toBeTruthy();
	});
});
