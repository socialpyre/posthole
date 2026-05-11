import * as esbuild from "esbuild";

const watch = process.argv.includes("--watch");

const options = {
  entryPoints: ["src/posthole/ui/main.ts"],
  bundle: true,
  format: "esm",
  target: "es2022",
  outfile: "src/posthole/static/app.js",
  sourcemap: true,
  minify: !watch,
  logLevel: "info",
};

if (watch) {
  const ctx = await esbuild.context(options);
  await ctx.watch();
  console.log("esbuild: watching src/posthole/ui/main.ts → src/posthole/static/app.js");
} else {
  await esbuild.build(options);
}
