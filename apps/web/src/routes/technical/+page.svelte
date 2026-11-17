<script lang="ts">
	const capabilities = [
		{
			name: 'MITRE ATT&CK',
			state: 'Available in published context',
			detail:
				'Technique identifiers and names remain linked to actor behaviors, observations and advisory sections.',
			href: '/search?q=T1059.001',
			action: 'Search a technique'
		},
		{
			name: 'Sigma',
			state: 'Operator workflow',
			detail:
				'Validated rule artifacts stay in the protected technical-artifact workflow. Public generation requires a separate security review.',
			href: null,
			action: null
		},
		{
			name: 'STIX 2.1',
			state: 'Operator export',
			detail:
				'Deterministic bundles are available through the authenticated export boundary and are not generated in an anonymous browser session.',
			href: null,
			action: null
		}
	] as const;
</script>

<svelte:head>
	<title>Technical intelligence | WATCHTOWER</title>
	<meta
		name="description"
		content="Understand WATCHTOWER ATT&CK, Sigma and STIX capability boundaries."
	/>
</svelte:head>

<section class="technical-page">
	<header>
		<p>TECHNICAL CONTEXT / SAFE PUBLIC BOUNDARY</p>
		<h1>Technical intelligence</h1>
		<span
			>Standards and detection formats stay connected to evidence without exposing operator
			controls.</span
		>
	</header>

	<ol>
		{#each capabilities as capability, index (capability.name)}
			<li>
				<span class="index">{String(index + 1).padStart(2, '0')}</span>
				<div>
					<p>{capability.state}</p>
					<h2>{capability.name}</h2>
					<span>{capability.detail}</span>
					{#if capability.href && capability.action}
						<a href={capability.href}>{capability.action}<span aria-hidden="true"> →</span></a>
					{/if}
				</div>
			</li>
		{/each}
	</ol>
</section>

<style>
	.technical-page {
		max-width: 70rem;
		margin: 0 auto;
		padding: var(--space-8) var(--space-5);
	}

	header {
		max-width: 54rem;
		padding-bottom: var(--space-7);
	}

	header p,
	li p,
	.index {
		font-family: var(--font-mono);
		font-size: var(--font-size-xs);
		letter-spacing: var(--letter-spacing-label);
	}

	header p,
	li p {
		margin: 0;
		color: var(--color-primary);
		font-weight: 700;
		text-transform: uppercase;
	}

	h1 {
		margin: var(--space-2) 0;
		font-size: var(--font-size-xl);
	}

	header > span,
	li div > span {
		color: var(--color-ink-muted);
	}

	ol {
		margin: 0;
		padding: 0;
		border-top: var(--border-width) solid var(--color-border-strong);
		list-style: none;
	}

	li {
		display: grid;
		grid-template-columns: 3rem minmax(0, 1fr);
		gap: var(--space-4);
		padding: var(--space-6) 0;
		border-bottom: var(--border-width) solid var(--color-border);
	}

	.index {
		color: var(--color-secondary);
	}

	h2 {
		margin: var(--space-2) 0 var(--space-3);
		font-size: clamp(1.45rem, 3vw, 2.2rem);
	}

	a {
		display: inline-flex;
		min-height: 2.75rem;
		align-items: center;
		margin-top: var(--space-3);
		color: var(--color-primary);
		font-weight: 700;
		text-decoration: none;
	}
</style>
