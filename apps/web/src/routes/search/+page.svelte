<svelte:head>
	<title>Research | WATCHTOWER</title>
</svelte:head>

<section class="workspace-intro" aria-labelledby="research-title">
	<div class="intro-inner">
		<p class="eyebrow">INTELLIGENCE RESEARCH</p>
		<h1 id="research-title">Track adversaries. <span>Follow the evidence.</span></h1>
		<p class="lede">
			WATCHTOWER brings published intelligence, actor evolution, and source context into one private
			research workspace.
		</p>

		<div class="foundation-panel">
			<div>
				<p class="panel-label">WORKSPACE STATUS</p>
				<h2>Research foundation online</h2>
				<p>Search and evidence modules will appear as each reviewed capability is enabled.</p>
			</div>
			<span class="status-chip"><span aria-hidden="true"></span> READY</span>
		</div>
	</div>
</section>

<style>
	.workspace-intro {
		min-height: calc(100vh - var(--header-height));
		background-color: var(--color-canvas);
		background-image: var(--texture-grid);
		background-size: var(--grid-size) var(--grid-size);
	}

	.intro-inner {
		max-width: var(--content-width);
		margin: 0 auto;
		padding: var(--space-8) var(--space-5);
	}

	.eyebrow,
	.panel-label {
		margin: 0;
		color: var(--color-primary);
		font-family: var(--font-mono);
		font-size: var(--font-size-xs);
		font-weight: 700;
		letter-spacing: var(--letter-spacing-label);
	}

	h1 {
		max-width: 17ch;
		margin: var(--space-4) 0;
		font-size: var(--font-size-xl);
		line-height: var(--line-height-tight);
		letter-spacing: -0.035em;
	}

	h1 span {
		background: var(--gradient-brand);
		background-clip: text;
		color: transparent;
	}

	.lede {
		max-width: 44rem;
		margin: 0;
		color: var(--color-ink-muted);
		font-size: var(--font-size-lg);
	}

	.foundation-panel {
		display: flex;
		max-width: 58rem;
		align-items: flex-start;
		justify-content: space-between;
		gap: var(--space-5);
		margin-top: var(--space-7);
		padding: var(--space-6);
		border: var(--border-width) solid var(--color-border-strong);
		border-radius: var(--radius-lg);
		background: var(--color-surface);
		box-shadow: var(--shadow-panel);
	}

	.foundation-panel h2 {
		margin: var(--space-2) 0;
		font-size: var(--font-size-lg);
	}

	.foundation-panel p:last-child {
		margin: 0;
		color: var(--color-ink-muted);
	}

	.status-chip {
		display: inline-flex;
		flex: none;
		align-items: center;
		gap: var(--space-2);
		padding: var(--space-1) var(--space-2);
		border: var(--border-width) solid var(--color-observed);
		border-radius: var(--radius-sm);
		color: var(--color-observed);
		font-family: var(--font-mono);
		font-size: var(--font-size-xs);
		font-weight: 700;
		letter-spacing: var(--letter-spacing-label);
	}

	.status-chip span {
		width: var(--space-2);
		height: var(--space-2);
		border-radius: 50%;
		background: currentColor;
	}

	@media (max-width: 40rem) {
		.foundation-panel {
			flex-direction: column;
			padding: var(--space-5);
		}
	}
</style>
