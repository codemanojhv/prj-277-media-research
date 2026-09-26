import { getCloudflareContext } from "@opennextjs/cloudflare";
import { handleCloudflareApi, type EdgeEnvironment } from "@/lib/cloudflare-api";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

async function dispatch(request: Request) {
  const { env } = getCloudflareContext();
  return handleCloudflareApi(request, env as EdgeEnvironment);
}

export const GET = dispatch;
export const POST = dispatch;
export const OPTIONS = dispatch;
