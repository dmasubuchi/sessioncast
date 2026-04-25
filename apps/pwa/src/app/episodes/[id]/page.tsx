// Static export requires generateStaticParams for dynamic routes.
// Episode IDs are only known at runtime, so we return [] and rely on CSR.
export function generateStaticParams() {
  return [];
}

import EpisodeDetailClient from "./EpisodeDetailClient";

export default function EpisodeDetailPage({
  params,
}: {
  params: { id: string };
}) {
  return <EpisodeDetailClient id={params.id} />;
}
