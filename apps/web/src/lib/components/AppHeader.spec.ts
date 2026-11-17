import { render, screen } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';
import AppHeader from './AppHeader.svelte';

describe('AppHeader', () => {
	it('exposes the public module navigation and current destination', () => {
		render(AppHeader, {
			environmentLabel: 'LOCAL / PRIVATE',
			currentPath: '/search',
			adminEnabled: false
		});

		expect(screen.getByRole('link', { name: 'WATCHTOWER home' }).getAttribute('href')).toBe('/');
		expect(screen.getByRole('link', { name: 'Research' }).getAttribute('aria-current')).toBe(
			'page'
		);
		for (const label of ['Home', 'Intelligence', 'Actors', 'Evolution', 'Technical']) {
			expect(screen.getByRole('link', { name: label })).toBeTruthy();
		}
		expect(screen.getByRole('link', { name: 'Platform updates' })).toBeTruthy();
		expect(screen.queryByRole('link', { name: 'Admin integrations' })).toBeNull();
		expect(screen.getByText('LOCAL / PRIVATE')).toBeTruthy();
	});

	it('shows the private operator destination only when enabled', () => {
		render(AppHeader, {
			environmentLabel: 'LOCAL / PRIVATE',
			currentPath: '/admin/integrations',
			adminEnabled: true
		});

		const admin = screen.getByRole('link', { name: 'Admin integrations' });
		expect(admin.getAttribute('href')).toBe('/admin/integrations');
		expect(admin.getAttribute('class')).toContain('active');
	});
});
