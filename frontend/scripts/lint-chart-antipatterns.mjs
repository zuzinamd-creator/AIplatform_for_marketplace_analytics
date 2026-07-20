/**
 * Chart anti-pattern lint (P0 Ledger UI).
 * Fail if source introduces pie>4 segments, dual-axis charts, or decorative 3D.
 * Run: node scripts/lint-chart-antipatterns.mjs
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SRC = path.resolve(__dirname, "../src");

const FORBIDDEN = [
  { id: "pie-chart-import", re: /\bPieChart\b/, msg: "PieChart is forbidden (use bar/line; max 4 segments not enough for pie policy)" },
  { id: "radar-chart", re: /\bRadarChart\b/, msg: "RadarChart is forbidden (decorative)" },
  { id: "treemap", re: /\bTreemap\b/, msg: "Treemap is forbidden on seller dashboard charts" },
  { id: "funnel", re: /\bFunnelChart\b/, msg: "FunnelChart is forbidden" },
  { id: "3d-css", re: /preserve-3d|perspective\(|rotateX\(|rotateY\(/i, msg: "3D / decorative perspective transforms forbidden on charts UI" },
  { id: "dual-yaxis", re: /yAxisId\s*=/, msg: "Dual-axis charts (yAxisId) are forbidden" },
];

function walk(dir, out = []) {
  for (const name of fs.readdirSync(dir)) {
    const p = path.join(dir, name);
    const st = fs.statSync(p);
    if (st.isDirectory()) {
      if (name === "node_modules" || name === "dist") continue;
      walk(p, out);
    } else if (/\.(tsx|ts|jsx|js|css)$/.test(name)) {
      out.push(p);
    }
  }
  return out;
}

function main() {
  const files = walk(SRC);
  const hits = [];
  for (const file of files) {
    const text = fs.readFileSync(file, "utf8");
    // Skip the lint script's own docs and this checker if ever colocated
    if (file.includes("lint-chart-antipatterns")) continue;
    for (const rule of FORBIDDEN) {
      if (rule.re.test(text)) {
        hits.push({ file: path.relative(path.resolve(__dirname, ".."), file), rule: rule.id, msg: rule.msg });
      }
    }
  }
  if (hits.length) {
    console.error("Chart anti-pattern lint FAILED:");
    for (const h of hits) {
      console.error(`  [${h.rule}] ${h.file}: ${h.msg}`);
    }
    process.exit(1);
  }
  console.log(`Chart anti-pattern lint OK (${files.length} files).`);
}

main();
