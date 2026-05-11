import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "jsdom",
    include: ["src/posthole/ui/**/__specs__/*.spec.ts"],
    globals: false,
  },
});
