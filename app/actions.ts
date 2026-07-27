"use server";

import { execFile } from "node:child_process";
import path from "node:path";
import { promisify } from "node:util";

import { revalidatePath } from "next/cache";

const execFileAsync = promisify(execFile);

const PIPELINE_DIR = path.join(process.cwd(), "pipeline");
const COMMAND_TIMEOUT_MS = 120_000;

// Guards against overlapping runs from a second tab/window -- the client only
// serializes actions dispatched from the same tab, not across tabs.
let isRefreshing = false;

type ExecError = Error & { stdout?: string; stderr?: string };

async function runPipelineCommand(command: string): Promise<string> {
  try {
    const { stdout } = await execFileAsync("uv", ["run", "pipeline", command], {
      cwd: PIPELINE_DIR,
      timeout: COMMAND_TIMEOUT_MS,
    });
    // Only the "X complete: ..." summary line -- `predict` also prints one
    // line per skipped player, which would otherwise flood the UI.
    return stdout.trim().split("\n")[0];
  } catch (error) {
    const execError = error as ExecError;
    const detail = execError.stderr?.trim() || execError.stdout?.trim() || execError.message;
    throw new Error(`"${command}" failed: ${detail}`);
  }
}

export type RefreshResult = {
  success: boolean;
  message: string;
};

export async function refreshData(): Promise<RefreshResult> {
  if (isRefreshing) {
    return { success: false, message: "A refresh is already in progress." };
  }

  isRefreshing = true;
  try {
    let ingestOutput: string;
    try {
      ingestOutput = await runPipelineCommand("ingest");
    } catch (error) {
      // Don't run predict against a failed/partial ingest -- leave existing predictions untouched.
      return { success: false, message: (error as Error).message };
    }

    let predictOutput: string;
    try {
      predictOutput = await runPipelineCommand("predict");
    } catch (error) {
      return { success: false, message: (error as Error).message };
    }

    revalidatePath("/");
    return { success: true, message: `${ingestOutput}\n${predictOutput}` };
  } finally {
    isRefreshing = false;
  }
}
