<script lang="ts">
	import './layout.css';
	import AppHeader from '#lib/components/AppHeader.svelte';
	import type { LayoutProps } from './$types';

	let { children, data }: LayoutProps = $props();
</script>

<svelte:head>
	<title>WATCHTOWER</title>
	<meta
		name="description"
		content="Private adversary intelligence research with explicit provenance and evidence."
	/>
</svelte:head>

<a class="skip-link" href="#main-content">Skip to main content</a>
<AppHeader environmentLabel={data.environmentLabel} currentPath={data.currentPath} />

<main id="main-content" tabindex="-1">
	{@render children()}
</main>

<style>
	.skip-link {
		position: fixed;
		top: var(--space-3);
		left: var(--space-3);
		z-index: 20;
		transform: translateY(-200%);
		padding: var(--space-2) var(--space-3);
		border: var(--border-width) solid var(--color-primary);
		border-radius: var(--radius-sm);
		background: var(--color-surface-raised);
		color: var(--color-primary);
		transition: transform var(--motion-fast) var(--easing-standard);
	}

	.skip-link:focus {
		transform: translateY(0);
	}

	main {
		min-height: calc(100vh - var(--header-height));
	}
</style>
