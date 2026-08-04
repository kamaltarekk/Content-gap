import { projectTokens } from "@cgi/database";
import { type Db } from "@cgi/database";
import { sha256, timingSafeEqualHex } from "@cgi/shared";
import { eq } from "drizzle-orm";

// Project-scoped bearer token auth. Tokens are SHA-256 hashed at rest and compared in
// constant time. The extension never holds the Anthropic key — only this token.

export interface AuthedProject {
  projectId: string;
  tokenId: string;
}

export async function verifyToken(db: Db, authHeader: string | undefined): Promise<AuthedProject | null> {
  if (!authHeader) return null;
  const token = authHeader.replace(/^Bearer\s+/i, "").trim();
  if (!token) return null;
  const hash = sha256(token);
  const rows = await db.select().from(projectTokens).where(eq(projectTokens.tokenHash, hash)).limit(1);
  const row = rows[0];
  if (!row) return null;
  if (!timingSafeEqualHex(row.tokenHash, hash)) return null;
  if (row.expiresAt && row.expiresAt.getTime() < Date.now()) return null;
  await db.update(projectTokens).set({ lastUsedAt: new Date() }).where(eq(projectTokens.id, row.id));
  return { projectId: row.projectId, tokenId: row.id };
}
