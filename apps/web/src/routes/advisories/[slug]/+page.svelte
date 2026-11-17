<script lang="ts">
	import type { PageProps } from './$types';
	import AdvisoryDetail from '#lib/components/AdvisoryDetail.svelte';
	import StatePanel from '#lib/components/StatePanel.svelte';

	let { data }: PageProps = $props();
</script>

<svelte:head>
	<title>{data.response?.data.revision.title ?? 'Published advisory'} | WATCHTOWER</title>
</svelte:head>

{#if data.view === 'success' && data.response}
	<AdvisoryDetail
		response={data.response}
		initialUpdates={data.updates?.data ?? []}
		updatesUnavailable={Boolean(data.updatesError)}
		updatesRequestId={data.updatesError?.requestId ?? null}
	/>
{:else}
	<div class="unavailable">
		<StatePanel
			state="error"
			title="Published advisory unavailable"
			message={data.error?.message ?? 'This published record is unavailable.'}
			requestId={data.error?.requestId ?? undefined}
		/>
	</div>
{/if}

<style>
	.unavailable {
		max-width: 54rem;
		margin: 0 auto;
		padding: var(--space-8) var(--space-5);
	}
</style>
