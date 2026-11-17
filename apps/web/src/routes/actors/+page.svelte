<script lang="ts">
	import type { PageProps } from './$types';
	import ActorDiscovery from '#lib/components/ActorDiscovery.svelte';
	import StatePanel from '#lib/components/StatePanel.svelte';

	let { data }: PageProps = $props();
</script>

<svelte:head>
	<title>Threat actors | WATCHTOWER</title>
	<meta name="description" content="Browse recently observed and active published threat actors." />
</svelte:head>

<section class="directory">
	<header>
		<p>ACTOR DIRECTORY / PUBLISHED PROFILES</p>
		<h1>Threat actors</h1>
		<span>Identity, aliases, behaviors, techniques, activity and supporting evidence.</span>
	</header>
	<form action="/search" method="GET" role="search">
		<label for="actor-query">Find an actor, alias, technique or indicator</label>
		<div>
			<input
				id="actor-query"
				name="q"
				type="search"
				minlength="2"
				maxlength="200"
				placeholder="Search published actor context"
			/>
			<input type="hidden" name="entity_type" value="actor" />
			<input type="hidden" name="entity_type" value="alias" />
			<button type="submit">Search directory <span aria-hidden="true">→</span></button>
		</div>
	</form>
	{#if data.error}
		<StatePanel
			state="error"
			title="Actor directory unavailable"
			message={data.error.message}
			requestId={data.error.requestId ?? undefined}
		/>
	{:else}
		<ActorDiscovery discovery={data.discovery} />
	{/if}
</section>

<style>
	.directory {
		max-width: var(--content-width);
		margin: 0 auto;
		padding: var(--space-8) var(--space-5);
	}

	.directory > header {
		max-width: 52rem;
		margin-bottom: var(--space-6);
	}

	header p {
		margin: 0;
		color: var(--color-primary);
		font-family: var(--font-mono);
		font-size: var(--font-size-xs);
		font-weight: 700;
		letter-spacing: var(--letter-spacing-label);
	}

	h1 {
		margin: var(--space-2) 0;
		font-size: var(--font-size-xl);
		line-height: var(--line-height-tight);
	}

	header span,
	label {
		color: var(--color-ink-muted);
	}

	form {
		margin-bottom: var(--space-7);
	}

	label {
		display: block;
		margin-bottom: var(--space-2);
		font-size: var(--font-size-sm);
		font-weight: 700;
	}

	form div {
		display: grid;
		grid-template-columns: minmax(0, 1fr) auto;
		border-bottom: var(--border-width) solid var(--color-border-strong);
		background: var(--color-surface-glass);
	}

	input:not([type='hidden']) {
		min-width: 0;
		min-height: 3.5rem;
		padding: 0 var(--space-4);
		border: 0;
		outline: 0;
		background: transparent;
		color: var(--color-ink);
	}

	button {
		min-height: 3.5rem;
		padding: 0 var(--space-5);
		border: 0;
		background: var(--color-primary);
		color: var(--color-canvas);
		font-weight: 800;
		cursor: pointer;
	}

	@media (max-width: 38rem) {
		form div {
			grid-template-columns: 1fr;
		}
	}
</style>
