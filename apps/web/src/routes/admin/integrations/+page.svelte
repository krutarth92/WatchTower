<script lang="ts">
	import UtcDate from '#lib/components/UtcDate.svelte';
	import type { IntegrationRead } from '#lib/integrations/contracts.ts';
	import type { PageProps } from './$types';

	let { data, form }: PageProps = $props();

	const waveLabels = {
		implemented: 'In service',
		first_wave: 'Next source wave',
		second_wave: 'Later source wave',
		candidate: 'Candidate'
	} as const;

	const enrichmentWaveLabels = {
		implemented: 'In service',
		first_wave: 'Next enrichment',
		later: 'When a use case requires it'
	} as const;

	function stateLabel(integration: IntegrationRead) {
		if (integration.can_sync) return 'READY';
		if (integration.implemented) return 'CONFIGURATION REQUIRED';
		return 'PLANNED';
	}
</script>

<svelte:head>
	<title>Integration administration | WATCHTOWER</title>
	<meta
		name="description"
		content="Private operator view of WATCHTOWER intelligence sources and enrichment roadmap."
	/>
</svelte:head>

<article class="integration-page">
	<header class="page-intro">
		<p>OPERATOR / INTEGRATION CONTROL</p>
		<h1>Intelligence sources</h1>
		<span>
			Review what WATCHTOWER can ingest today, what comes next, and which enrichment is planned.
			Credentials remain on the server.
		</span>
	</header>

	{#if form?.message}
		<div class:failure={form.ok === false} class="action-result" role="status">
			<strong>{form.ok === false ? 'Refresh not queued' : 'Request accepted'}</strong>
			<span>{form.message}</span>
			{#if form.requestId}<small>Request {form.requestId}</small>{/if}
		</div>
	{/if}

	{#if data.loadError}
		<section class="unavailable" aria-labelledby="integration-unavailable">
			<p>OPERATIONAL STATE</p>
			<h2 id="integration-unavailable">Integration state unavailable</h2>
			<span>{data.loadError.message}</span>
			{#if data.loadError.requestId}<small>Request {data.loadError.requestId}</small>{/if}
		</section>
	{:else if data.catalog}
		<section class="source-register" aria-labelledby="source-register-heading">
			<div class="section-heading">
				<div>
					<p>APPROVED SOURCE REGISTER</p>
					<h2 id="source-register-heading">Connector roadmap</h2>
				</div>
				<span>{data.catalog.data.length} reviewed sources</span>
			</div>

			<ol>
				{#each data.catalog.data as integration, index (integration.key)}
					<li>
						<div class="sequence">{String(index + 1).padStart(2, '0')}</div>
						<div class="source-copy">
							<div class="source-title">
								<div>
									<p>{waveLabels[integration.wave]}</p>
									<h3>{integration.name}</h3>
								</div>
								<span class:ready={integration.can_sync}>{stateLabel(integration)}</span>
							</div>
							<p class="description">{integration.description}</p>

							<div class="source-detail">
								<div>
									<strong>Enrichment</strong>
									<span>{integration.enrichments.join(' · ') || 'Defined with implementation'}</span
									>
								</div>
								{#if integration.required_settings.length > 0}
									<div>
										<strong>Server setting</strong>
										<code>{integration.required_settings.join(', ')}</code>
									</div>
								{/if}
								{#if integration.latest_job}
									<div>
										<strong>Latest refresh</strong>
										<span>
											{integration.latest_job.state.toUpperCase()} ·
											<UtcDate value={integration.latest_job.updated_at} />
										</span>
									</div>
								{/if}
							</div>

							{#if integration.can_sync && integration.job_kind}
								<form method="POST" action="?/sync">
									<input type="hidden" name="integration_key" value={integration.key} />
									<input type="hidden" name="idempotency_key" value={data.idempotencyKey} />
									<button type="submit"
										>Queue {integration.name} refresh <span aria-hidden="true">→</span></button
									>
								</form>
							{/if}
						</div>
					</li>
				{/each}
			</ol>
		</section>

		<section class="enrichment-register" aria-labelledby="enrichment-heading">
			<div class="section-heading">
				<div>
					<p>CONTEXT PIPELINE</p>
					<h2 id="enrichment-heading">Enrichment roadmap</h2>
				</div>
				<span>Evidence-backed context, added in deliberate stages</span>
			</div>
			<ul>
				{#each data.catalog.enrichment_roadmap as enrichment (enrichment.key)}
					<li>
						<div>
							<p>{enrichmentWaveLabels[enrichment.wave]}</p>
							<h3>{enrichment.name}</h3>
						</div>
						<span>{enrichment.description}</span>
					</li>
				{/each}
			</ul>
		</section>
	{/if}
</article>

<style>
	.integration-page {
		max-width: 72rem;
		margin: 0 auto;
		padding: var(--space-8) var(--space-5);
	}

	.page-intro {
		max-width: 54rem;
		padding-bottom: var(--space-7);
	}

	.page-intro p,
	.section-heading p,
	.source-title p,
	.enrichment-register li p,
	.sequence {
		margin: 0;
		font-family: var(--font-mono);
		font-size: var(--font-size-xs);
		letter-spacing: var(--letter-spacing-label);
		text-transform: uppercase;
	}

	.page-intro p,
	.section-heading p,
	.source-title p,
	.enrichment-register li p {
		color: var(--color-primary);
		font-weight: 700;
	}

	h1 {
		margin: var(--space-3) 0;
		font-size: var(--font-size-xl);
		line-height: var(--line-height-tight);
	}

	.page-intro > span,
	.section-heading > span,
	.description,
	.enrichment-register li > span,
	.unavailable > span {
		color: var(--color-ink-muted);
	}

	.action-result,
	.unavailable {
		display: grid;
		gap: var(--space-1);
		margin-bottom: var(--space-6);
		padding: var(--space-4) 0 var(--space-4) var(--space-4);
		border-left: var(--space-1) solid var(--color-observed);
	}

	.action-result.failure,
	.unavailable {
		border-left-color: var(--color-critical);
	}

	.action-result span,
	.action-result small,
	.unavailable small {
		color: var(--color-ink-muted);
	}

	.source-register,
	.enrichment-register {
		margin-top: var(--space-6);
	}

	.section-heading {
		display: flex;
		align-items: end;
		justify-content: space-between;
		gap: var(--space-5);
		padding-bottom: var(--space-4);
		border-bottom: var(--border-width) solid var(--color-border-strong);
	}

	.section-heading h2,
	.unavailable h2 {
		margin: var(--space-2) 0 0;
		font-size: clamp(1.4rem, 3vw, 2rem);
	}

	ol,
	ul {
		margin: 0;
		padding: 0;
		list-style: none;
	}

	.source-register li {
		display: grid;
		grid-template-columns: 3rem minmax(0, 1fr);
		gap: var(--space-5);
		padding: var(--space-6) 0;
		border-bottom: var(--border-width) solid var(--color-border);
	}

	.sequence {
		color: var(--color-secondary);
	}

	.source-title {
		display: flex;
		align-items: start;
		justify-content: space-between;
		gap: var(--space-4);
	}

	.source-title h3,
	.enrichment-register h3 {
		margin: var(--space-1) 0 0;
		font-size: var(--font-size-lg);
	}

	.source-title > span {
		color: var(--color-ink-subtle);
		font-family: var(--font-mono);
		font-size: var(--font-size-xs);
		letter-spacing: var(--letter-spacing-label);
		white-space: nowrap;
	}

	.source-title > span.ready {
		color: var(--color-observed);
	}

	.description {
		max-width: 52rem;
		margin: var(--space-3) 0;
	}

	.source-detail {
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-2) var(--space-6);
	}

	.source-detail > div {
		display: grid;
		gap: var(--space-1);
	}

	.source-detail strong {
		color: var(--color-ink-subtle);
		font-family: var(--font-mono);
		font-size: var(--font-size-xs);
		font-weight: 500;
		letter-spacing: var(--letter-spacing-label);
		text-transform: uppercase;
	}

	.source-detail span,
	.source-detail code {
		color: var(--color-ink-muted);
		font-size: var(--font-size-sm);
	}

	.source-detail code {
		overflow-wrap: anywhere;
	}

	form {
		margin-top: var(--space-4);
	}

	button {
		min-height: 2.75rem;
		padding: 0;
		border: 0;
		background: transparent;
		color: var(--color-primary);
		font-weight: 700;
		cursor: pointer;
	}

	button:hover {
		color: var(--color-focus);
	}

	.enrichment-register {
		padding-top: var(--space-7);
	}

	.enrichment-register ul {
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
	}

	.enrichment-register li {
		display: grid;
		grid-template-columns: minmax(10rem, 0.7fr) minmax(0, 1.3fr);
		gap: var(--space-5);
		padding: var(--space-5) var(--space-5) var(--space-5) 0;
		border-bottom: var(--border-width) solid var(--color-border);
	}

	@media (max-width: 52rem) {
		.enrichment-register ul {
			grid-template-columns: 1fr;
		}

		.enrichment-register li {
			padding-right: 0;
		}
	}

	@media (max-width: 38rem) {
		.integration-page {
			padding-inline: var(--space-4);
		}

		.section-heading,
		.source-title {
			align-items: flex-start;
			flex-direction: column;
		}

		.source-register li {
			grid-template-columns: 1fr;
			gap: var(--space-2);
		}

		.enrichment-register li {
			grid-template-columns: 1fr;
			gap: var(--space-2);
		}
	}
</style>
